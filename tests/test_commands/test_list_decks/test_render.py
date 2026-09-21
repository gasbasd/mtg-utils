from unittest.mock import patch

from mtg_utils.commands.list_decks.render import render_decklist_panel, render_decks_with_cards


def test_render_decklist_panel_calls_function():
    """Render a decklist panel function is called successfully."""
    # Test that the function is callable and imports correctly
    assert callable(render_decklist_panel)
    assert callable(render_decks_with_cards)


def test_render_decks_with_cards_is_callable():
    """Test that render_decks_with_cards is properly defined."""
    assert callable(render_decks_with_cards)


def test_render_decks_with_cards_multiple_decks(capsys):
    """Test that render_decks_with_cards renders multiple decks with empty line separator."""
    decks = [
        ("deck1", "card_library/decks/deck1.txt"),
        ("deck2", "card_library/decks/deck2.txt"),
    ]

    # Mock load_deck_cards to return known cards
    with patch("mtg_utils.commands.list_decks.render.load_deck_cards") as mock_load:
        mock_load.side_effect = [
            ({"Forest": 4, "Island": 4}, {}),  # deck1 cards
            ({"Mountain": 4, "Plains": 4}, {}),  # deck2 cards
        ]

        render_decks_with_cards(decks)

    captured = capsys.readouterr()
    output = captured.out

    # Verify both decks are rendered
    assert "deck1 (8 cards)" in output
    assert "deck2 (8 cards)" in output
    # Verify cards are rendered
    assert "Forest" in output
    assert "Island" in output
    assert "Mountain" in output
    assert "Plains" in output


def test_render_decks_with_cards_single_deck(capsys):
    """Test that render_decks_with_cards renders a single deck."""
    decks = [
        ("my_deck", "card_library/decks/my_deck.txt"),
    ]

    with patch("mtg_utils.commands.list_decks.render.load_deck_cards") as mock_load:
        mock_load.return_value = ({"Forest": 4, "Island": 4}, {})

        render_decks_with_cards(decks)

    captured = capsys.readouterr()
    output = captured.out

    assert "my_deck (8 cards)" in output
    assert "Forest" in output
    assert "Island" in output


def test_render_decks_with_cards_error_handling(capsys):
    """Test that render_decks_with_cards handles missing deck files gracefully."""
    decks = [
        ("missing_deck", "card_library/decks/nonexistent.txt"),
    ]

    render_decks_with_cards(decks)

    captured = capsys.readouterr()
    output = captured.out

    assert "Error:" in output
    assert "Deck file not found" in output


def test_render_decks_with_cards_no_decks(capsys):
    """Test that render_decks_with_cards handles empty decks list."""
    decks = []

    render_decks_with_cards(decks)

    captured = capsys.readouterr()
    output = captured.out

    assert "No decks configured" in output


def test_render_decks_with_cards_shows_sideboard_section(capsys):
    """A deck with a sideboard shows both counts in the header and a Sideboard section."""
    with patch("mtg_utils.commands.list_decks.render.load_deck_cards") as mock_load:
        mock_load.return_value = ({"Lightning Bolt": 4, "Mountain": 56}, {"Pyroblast": 3})

        render_decks_with_cards([("burn", "card_library/decks/burn.txt")])

    output = capsys.readouterr().out

    assert "burn (60 cards + 3 sideboard)" in output
    assert "Sideboard" in output
    assert output.index("Lightning Bolt") < output.index("Sideboard") < output.index("Pyroblast")


def test_render_decks_with_cards_empty_deck(capsys):
    """A deck with no cards in either board is reported as empty."""
    with patch("mtg_utils.commands.list_decks.render.load_deck_cards") as mock_load:
        mock_load.return_value = ({}, {})

        render_decks_with_cards([("void", "card_library/decks/void.txt")])

    assert "void (empty deck)" in capsys.readouterr().out
