from mtg_utils.utils.cards import parse_card_list, split_boards
from mtg_utils.utils.readers import read_list


def load_deck_cards(deck_file: str) -> tuple[dict[str, int], dict[str, int]]:
    """Load and parse deck cards from a file.

    Args:
        deck_file: Path to the deck file

    Returns:
        (mainboard, sideboard) dictionaries of {card_name: quantity}; the sideboard is empty
        when the file has no '# Sideboard' marker.
    """
    mainboard, sideboard = split_boards(read_list(deck_file))
    return parse_card_list(mainboard), parse_card_list(sideboard)
