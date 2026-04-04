from mtg_utils.commands.list_decks.logic import load_deck_cards


def test_load_deck_cards(tmp_path):
    """Load deck cards from a file."""
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("1 Forest\n1 Island\n2 Mountain\n")

    result = load_deck_cards(str(deck_file))

    assert result == {
        "Forest": 1,
        "Island": 1,
        "Mountain": 2,
    }


def test_load_deck_cards_empty(tmp_path):
    """Load deck cards from an empty file."""
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("")

    result = load_deck_cards(str(deck_file))

    assert result == {}


def test_load_deck_cards_whitespace(tmp_path):
    """Handle whitespace in deck file."""
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("  1 Forest  \n\n  1 Island  \n  \n")

    result = load_deck_cards(str(deck_file))

    assert result == {
        "Forest": 1,
        "Island": 1,
    }
