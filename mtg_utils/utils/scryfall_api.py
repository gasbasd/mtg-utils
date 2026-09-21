import time
from collections.abc import Callable

import requests

from mtg_utils.utils.console import err_console

COLLECTION_URL = "https://api.scryfall.com/cards/collection"
SEARCH_URL = "https://api.scryfall.com/cards/search"
BATCH_SIZE = 75
# Scryfall asks for under 10 requests a second. Throttling before every call keeps a long order
# comfortably inside that budget; the retry ladder is the safety net for when it slips anyway.
REQUEST_INTERVAL = 0.15
MAX_RETRIES = 3
MIN_RETRY_WAIT = 1.0
MAX_RETRY_WAIT = 30.0
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})

_last_request = 0.0
# Scryfall rejects the whole batch if any collector number is empty or over 10 characters.
MAX_COLLECTOR_NUMBER = 10
NOT_FOUND = 404

session = requests.Session()
session.headers.update({"User-Agent": "mtg-utils/0.1", "Accept": "application/json"})


def _throttle() -> None:
    """Hold off until REQUEST_INTERVAL has passed since the previous request."""
    global _last_request
    waiting = REQUEST_INTERVAL - (time.monotonic() - _last_request)
    if waiting > 0:
        time.sleep(waiting)
    _last_request = time.monotonic()


def _retry_wait(response: requests.Response, attempt: int) -> float:
    """How long to hold off before retrying.

    Scryfall's Retry-After is neither reliable nor stable: it sends 10 while the error body
    says the cooldown is 60, and drops to 0 mid-ladder. Its advice is therefore escalated on
    each attempt that proves it too short, and floored so a 0 cannot burn a retry instantly.
    """
    header = response.headers.get("Retry-After", "")
    base = float(header) if header.isdigit() else 2.0
    return min(max(base * (attempt + 1), MIN_RETRY_WAIT), MAX_RETRY_WAIT)


def _with_retries(send: Callable[[], requests.Response]) -> requests.Response:
    """Send a request, riding out rate limits and transient Scryfall failures.

    The final attempt's response is returned as-is, so an exhausted retry ladder surfaces as
    a normal HTTP error rather than being mistaken for an empty result.
    """
    for attempt in range(MAX_RETRIES):
        _throttle()
        response = send()
        if response.status_code not in RETRY_STATUSES:
            return response
        wait = _retry_wait(response, attempt)
        err_console.print(
            f"[yellow]⚠[/yellow] Scryfall returned {response.status_code}; retrying in {wait:.0f}s"
        )
        time.sleep(wait)

    _throttle()
    return send()


def _printing(card: dict) -> dict[str, str]:
    return {
        "name": card["name"],
        "set": card["set"].upper(),
        "collector_number": card["collector_number"],
    }


def _key(identifier: dict[str, str]) -> tuple[str, str]:
    return identifier["set"].upper(), identifier["collector_number"]


def _is_usable(identifier: dict[str, str]) -> bool:
    return bool(identifier["set"]) and 1 <= len(identifier["collector_number"]) <= MAX_COLLECTOR_NUMBER


def find_printings(identifiers: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    """Resolve {"set", "collector_number"} identifiers against Scryfall, 75 per request.

    Returns {(set, collector number): printing} for the identifiers Scryfall recognised.
    Unrecognised identifiers -- and ones Scryfall will not even accept -- are simply absent
    from the result.
    """
    found: dict[tuple[str, str], dict[str, str]] = {}
    usable = [identifier for identifier in identifiers if _is_usable(identifier)]
    for start in range(0, len(usable), BATCH_SIZE):
        batch = usable[start : start + BATCH_SIZE]
        response = _with_retries(lambda: session.post(COLLECTION_URL, json={"identifiers": batch}, timeout=30))
        response.raise_for_status()
        payload = response.json()
        missing = {_key(identifier) for identifier in payload.get("not_found", [])}
        matched = [identifier for identifier in batch if _key(identifier) not in missing]
        for identifier, card in zip(matched, payload.get("data", [])):
            found[_key(identifier)] = _printing(card)
    return found


def _search(query: str) -> dict[str, str] | None:
    """Run a Scryfall search, accepting the result only when it is unambiguous.

    A card CardTrader numbered in its own way is worth reporting, not guessing at.

    Only Scryfall's 404 ("your query didn't match any cards", which is also what an unknown
    set code gives) counts as a miss. Anything else -- a rate limit above all -- is raised,
    because silently reading it as "not found" would mark good rows unresolved at random.
    """
    response = _with_retries(lambda: session.get(SEARCH_URL, params={"q": query, "unique": "prints"}, timeout=30))
    if response.status_code == NOT_FOUND:
        return None
    response.raise_for_status()
    data = response.json().get("data", [])
    return _printing(data[0]) if len(data) == 1 else None


def search_in_set(name: str, set_code: str) -> dict[str, str] | None:
    """Find a printing by name within one set.

    This is what rescues sets numbered in their own scheme -- The List writes Sapphire Charm
    as MIR-89, while CardTrader reports plain 89 -- and Scryfall resolves the set aliases
    CardTrader uses (mb1 and plist both mean The List) for free.
    """
    return _search(f'!"{name}" set:{set_code}')


def search_printing(name: str, collector_number: str) -> dict[str, str] | None:
    """Last resort: find a printing by name, narrowed by collector number when there is one."""
    return _search(f'!"{name}" cn:"{collector_number}"' if collector_number else f'!"{name}"')
