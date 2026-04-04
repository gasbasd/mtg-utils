from rich.console import Console

from mtg_utils.utils.decklists import render_decklist


def test_render_decklist_with_cards():
    """Render a decklist with cards."""
    cards = {
        "Forest": 1,
        "Island": 2,
    }

    panel = render_decklist("Test Deck", cards)

    # Render to console to get string output
    console = Console(file=__import__("io").StringIO(), force_terminal=True)
    console.print(panel)
    output = console.file.getvalue()

    assert "Test Deck" in output
    assert "3 cards" in output
    assert "Forest" in output
    assert "Island" in output


def test_render_decklist_empty():
    """Render an empty decklist."""
    cards = {}

    panel = render_decklist("Empty Deck", cards)

    console = Console(file=__import__("io").StringIO(), force_terminal=True)
    console.print(panel)
    output = console.file.getvalue()

    assert "Empty Deck" in output
    assert "(empty deck)" in output


def test_render_decklist_sorted():
    """Decklist cards are sorted alphabetically."""
    cards = {
        "Zzz": 1,
        "Alpha": 2,
        "Middle": 3,
    }

    panel = render_decklist("Sorted Deck", cards)

    console = Console(file=__import__("io").StringIO(), force_terminal=True)
    console.print(panel)
    output = console.file.getvalue()

    # Check that cards are sorted
    alpha_idx = output.find("Alpha")
    middle_idx = output.find("Middle")
    zzz_idx = output.find("Zzz")

    assert alpha_idx < middle_idx < zzz_idx


def test_render_multiple_decks():
    """Render multiple decklists side-by-side."""
    from mtg_utils.utils.decklists import render_multiple_decks

    decks = [
        ("Deck 1", {"Forest": 1, "Island": 2}),
        ("Deck 2", {"Plains": 1, "Mountain": 1}),
    ]

    # Create a StringIO output to capture console output
    output_buffer = __import__("io").StringIO()
    test_console = Console(file=output_buffer, force_terminal=True)

    # Temporarily replace console with our test console
    import mtg_utils.utils.decklists as decklists_module

    original_console = decklists_module.console
    decklists_module.console = test_console

    try:
        render_multiple_decks(decks)
        output = output_buffer.getvalue()

        assert "Deck 1" in output
        assert "Deck 2" in output
        assert "Forest" in output
        assert "Island" in output
        assert "Plains" in output
        assert "Mountain" in output
    finally:
        decklists_module.console = original_console


def test_render_multiple_decks_empty():
    """Render empty list of decks returns early."""
    from mtg_utils.utils.decklists import render_multiple_decks

    # Should not raise any error
    render_multiple_decks([])


def test_render_multiple_decks_single():
    """Render a single deck in render_multiple_decks."""
    from mtg_utils.utils.decklists import render_multiple_decks

    decks = [("Only Deck", {"Forest": 1})]

    output_buffer = __import__("io").StringIO()
    test_console = Console(file=output_buffer, force_terminal=True)

    import mtg_utils.utils.decklists as decklists_module

    original_console = decklists_module.console
    decklists_module.console = test_console

    try:
        render_multiple_decks(decks)
        output = output_buffer.getvalue()

        assert "Only Deck" in output
        assert "Forest" in output
    finally:
        decklists_module.console = original_console
