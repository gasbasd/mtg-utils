from mtg_utils.utils.cards import parse_card_list
from mtg_utils.utils.readers import read_list


def load_deck_cards(deck_file: str) -> dict[str, int]:
    """Load and parse deck cards from a file.

    Args:
        deck_file: Path to the deck file

    Returns:
        Dictionary of {card_name: quantity}
    """
    cards = read_list(deck_file)
    return parse_card_list(cards)
