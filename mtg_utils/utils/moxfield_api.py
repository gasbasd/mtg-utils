import cloudscraper

from mtg_utils.utils.cards import SIDEBOARD_MARKER
from mtg_utils.utils.formats import BASIC_LANDS

scraper = cloudscraper.create_scraper()

SNOW_LANDS = frozenset(name for name in BASIC_LANDS if name.startswith("Snow-Covered "))


def library_sort_key(card_entry):
    # Extract the card name (everything after the first space)
    card_name = card_entry.split(' ', 1)[1]

    # Snow-covered lands go at the end, then alphabetically within each group
    if card_name in SNOW_LANDS:
        return (1, card_name)
    else:
        return (0, card_name)


def _board_lines(boards: dict, board: str) -> list[str]:
    cards = boards.get(board, {}).get("cards", {}).values()
    return sorted(f"{card['quantity']} {card['card']['name']}" for card in cards)


def get_deck_list(deck_id: str, include_sideboard: bool = False) -> list[str]:
    """Fetch a deck list from Moxfield by its ID.

    Commanders come first, then the mainboard. With ``include_sideboard`` a non-empty
    sideboard is appended after a ``SIDEBOARD_MARKER`` line.
    """
    response = scraper.get(f"https://api2.moxfield.com/v3/decks/all/{deck_id}")
    response.raise_for_status()  # Raise an error for bad responses

    boards = response.json()["boards"]
    deck_list = _board_lines(boards, "mainboard")
    commanders = boards.get("commanders", {}).get("cards", {}).values()
    for i, commander in enumerate(commanders):
        name = commander["card"]["name"]
        deck_list.insert(i, f"1 {name}")

    if include_sideboard:
        sideboard = _board_lines(boards, "sideboard")
        if sideboard:
            deck_list.append(SIDEBOARD_MARKER)
            deck_list.extend(sideboard)

    return deck_list

def get_library(binder_id: str) -> list[str]:
    """Fetch the library cards from Moxfield."""
    first_page = scraper.get(f"https://api2.moxfield.com/v1/trade-binders/{binder_id}/search?pageNumber=1&pageSize=100")
    first_page.raise_for_status()  # Raise an error for bad responses
    first_page_data = first_page.json()
    total_pages = first_page_data["totalPages"]
    total_data = first_page_data["data"]
    for page_number in range(2, total_pages + 1):
        response = scraper.get(f"https://api2.moxfield.com/v1/trade-binders/{binder_id}/search?pageNumber={page_number}&pageSize=100")
        response.raise_for_status()
        total_data += response.json()["data"]
    card_quantities = {}
    for card in total_data:
        quantity = card["quantity"]
        name = card["card"]["name"]
        if name in card_quantities:
            card_quantities[name] += quantity
        else:
            card_quantities[name] = quantity
    
    library = [f"{quantity} {name}" for name, quantity in card_quantities.items()]
    library.sort(key=library_sort_key)
    return library
