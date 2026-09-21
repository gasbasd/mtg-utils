from unittest.mock import MagicMock, patch

import pytest
import requests

import mtg_utils.utils.scryfall_api as scryfall_api
from mtg_utils.utils.scryfall_api import (
    BATCH_SIZE,
    MAX_COLLECTOR_NUMBER,
    MAX_RETRIES,
    MAX_RETRY_WAIT,
    MIN_RETRY_WAIT,
    REQUEST_INTERVAL,
    find_printings,
    search_in_set,
    search_printing,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _card(name, set_code, number):
    return {"name": name, "set": set_code, "collector_number": number}


def _response(payload, status=200, headers=None):
    response = MagicMock(status_code=status, headers=headers or {})
    response.json.return_value = payload
    return response


@pytest.fixture(autouse=True)
def _no_waiting(monkeypatch):
    """Make throttling and backoff instant, and forget the previous test's request clock."""
    monkeypatch.setattr(scryfall_api.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(scryfall_api, "_last_request", 0.0)


# ---------------------------------------------------------------------------
# find_printings
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_find_printings_keys_by_requested_identifier():
    payload = {"data": [_card("Spirit Link", "dmr", "274")], "not_found": [{"set": "MB1", "collector_number": "89"}]}

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.post.return_value = _response(payload)
        found = find_printings(
            [{"set": "DMR", "collector_number": "274"}, {"set": "MB1", "collector_number": "89"}]
        )

    assert found == {("DMR", "274"): {"name": "Spirit Link", "set": "DMR", "collector_number": "274"}}


@pytest.mark.unit
def test_find_printings_batches_large_requests():
    identifiers = [{"set": "DFT", "collector_number": str(n)} for n in range(BATCH_SIZE + 10)]

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.post.return_value = _response({"data": [], "not_found": []})
        find_printings(identifiers)

    assert session.post.call_count == 2
    assert len(session.post.call_args_list[0].kwargs["json"]["identifiers"]) == BATCH_SIZE
    assert len(session.post.call_args_list[1].kwargs["json"]["identifiers"]) == 10


@pytest.mark.unit
def test_find_printings_with_nothing_to_look_up():
    with patch("mtg_utils.utils.scryfall_api.session") as session:
        assert find_printings([]) == {}
    session.post.assert_not_called()


@pytest.mark.unit
def test_find_printings_drops_identifiers_scryfall_would_reject():
    """An empty or overlong collector number makes Scryfall 400 the whole batch."""
    identifiers = [
        {"set": "PLIST2", "collector_number": ""},
        {"set": "", "collector_number": "12"},
        {"set": "DFT", "collector_number": "1" * (MAX_COLLECTOR_NUMBER + 1)},
        {"set": "DMR", "collector_number": "274"},
    ]

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.post.return_value = _response({"data": [_card("Spirit Link", "dmr", "274")], "not_found": []})
        found = find_printings(identifiers)

    assert session.post.call_args.kwargs["json"] == {"identifiers": [{"set": "DMR", "collector_number": "274"}]}
    assert list(found) == [("DMR", "274")]


@pytest.mark.unit
def test_find_printings_makes_no_request_when_nothing_is_usable():
    with patch("mtg_utils.utils.scryfall_api.session") as session:
        assert find_printings([{"set": "PLIST2", "collector_number": ""}]) == {}
    session.post.assert_not_called()


@pytest.mark.unit
def test_find_printings_propagates_http_errors():
    response = _response({}, status=503)
    response.raise_for_status.side_effect = requests.HTTPError("boom")

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.post.return_value = response
        with pytest.raises(requests.HTTPError):
            find_printings([{"set": "DFT", "collector_number": "1"}])


# ---------------------------------------------------------------------------
# search_printing
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_search_printing_returns_a_unique_match():
    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = _response({"data": [_card("Smashing Spree", "msc", "856")]})
        assert search_printing("Smashing Spree", "856") == {
            "name": "Smashing Spree",
            "set": "MSC",
            "collector_number": "856",
        }


@pytest.mark.unit
def test_search_printing_refuses_to_guess_between_matches():
    payload = {"data": [_card("Lightning Bolt", "pw26", "5"), _card("Lightning Bolt", "slp", "37")]}

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = _response(payload)
        assert search_printing("Lightning Bolt", "2") is None


@pytest.mark.unit
def test_search_printing_without_a_collector_number_searches_by_name_alone():
    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = _response({"data": [_card("Confound", "plst", "MIR-89")]})
        search_printing("Confound", "")

    assert session.get.call_args.kwargs["params"]["q"] == '!"Confound"'


@pytest.mark.unit
def test_search_printing_handles_no_results():
    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = _response({"details": "no cards"}, status=404)
        assert search_printing("Nonesuch", "1") is None


# ---------------------------------------------------------------------------
# search_in_set
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_search_in_set_finds_a_card_numbered_its_own_way():
    """The List writes Sapphire Charm as MIR-89; CardTrader reports plain 89."""
    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = _response({"data": [_card("Sapphire Charm", "plst", "MIR-89")]})
        printing = search_in_set("Sapphire Charm", "MB1")

    assert session.get.call_args.kwargs["params"]["q"] == '!"Sapphire Charm" set:MB1'
    assert printing == {"name": "Sapphire Charm", "set": "PLST", "collector_number": "MIR-89"}


@pytest.mark.unit
def test_search_in_set_refuses_to_guess_between_matches():
    payload = {"data": [_card("Foo", "abc", "1"), _card("Foo", "abc", "2")]}

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = _response(payload)
        assert search_in_set("Foo", "ABC") is None


@pytest.mark.unit
def test_search_in_set_handles_an_unknown_set():
    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = _response({"details": "no cards"}, status=404)
        assert search_in_set("Confound", "PLIST2") is None


@pytest.mark.unit
def test_search_raises_on_a_rate_limit_rather_than_reporting_a_miss():
    """A 429 read as "not found" would mark good rows unresolved at random."""
    response = _response({"details": "You are being rate-limited"}, status=429)
    response.raise_for_status.side_effect = requests.HTTPError("429")

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = response
        with pytest.raises(requests.HTTPError):
            search_printing("Terramorphic Expanse", "828")


# ---------------------------------------------------------------------------
# rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_requests_are_throttled_to_the_scryfall_interval(monkeypatch):
    slept = []
    monkeypatch.setattr(scryfall_api.time, "sleep", slept.append)
    monkeypatch.setattr(scryfall_api.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(scryfall_api, "_last_request", 100.0)

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = _response({"data": []})
        search_printing("Attercop", "116")

    assert slept == [REQUEST_INTERVAL]


@pytest.mark.unit
def test_a_rate_limit_is_retried_and_announced(capsys):
    limited = _response({"details": "rate-limited"}, status=429)
    ok = _response({"data": [_card("Spirit Link", "dmr", "274")]})

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.side_effect = [limited, ok]
        printing = search_printing("Spirit Link", "274")

    assert printing == {"name": "Spirit Link", "set": "DMR", "collector_number": "274"}
    assert session.get.call_count == 2
    assert "429" in capsys.readouterr().err


@pytest.mark.unit
def test_scryfalls_retry_after_is_honoured_but_capped(monkeypatch):
    slept = []
    monkeypatch.setattr(scryfall_api.time, "sleep", slept.append)
    limited = _response({}, status=503, headers={"Retry-After": "600"})
    ok = _response({"data": []})

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.side_effect = [limited, ok]
        search_printing("Attercop", "116")

    assert MAX_RETRY_WAIT in slept


@pytest.mark.unit
def test_the_wait_escalates_when_scryfalls_advice_proves_too_short(monkeypatch):
    """Scryfall sends Retry-After: 10 while the body admits the cooldown is 60."""
    slept = []
    monkeypatch.setattr(scryfall_api.time, "sleep", slept.append)
    limited = _response({}, status=429, headers={"Retry-After": "10"})
    ok = _response({"data": []})

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.side_effect = [limited, limited, ok]
        search_printing("Attercop", "116")

    assert [wait for wait in slept if wait >= 10] == [10.0, 20.0]


@pytest.mark.unit
def test_a_zero_retry_after_still_waits(monkeypatch):
    """Scryfall drops Retry-After to 0 mid-ladder; retrying instantly would burn an attempt."""
    slept = []
    monkeypatch.setattr(scryfall_api.time, "sleep", slept.append)
    limited = _response({}, status=429, headers={"Retry-After": "0"})
    ok = _response({"data": []})

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.side_effect = [limited, ok]
        search_printing("Attercop", "116")

    assert MIN_RETRY_WAIT in slept


@pytest.mark.unit
def test_a_server_error_is_retried_then_surfaced():
    """An exhausted ladder must raise, not look like an empty result."""
    failing = _response({}, status=503)
    failing.raise_for_status.side_effect = requests.HTTPError("503")

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.get.return_value = failing
        with pytest.raises(requests.HTTPError):
            search_printing("Attercop", "116")

    assert session.get.call_count == MAX_RETRIES + 1


@pytest.mark.unit
def test_batch_lookups_are_retried_too():
    limited = _response({}, status=429)
    ok = _response({"data": [_card("Spirit Link", "dmr", "274")], "not_found": []})

    with patch("mtg_utils.utils.scryfall_api.session") as session:
        session.post.side_effect = [limited, ok]
        found = find_printings([{"set": "DMR", "collector_number": "274"}])

    assert list(found) == [("DMR", "274")]
    assert session.post.call_count == 2
