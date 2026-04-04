from rich.markup import escape
from rich.panel import Panel

from mtg_utils.utils.console import console
from mtg_utils.utils.panels import card_table, side_by_side


def render_decklist(deck_name: str, cards: dict[str, int], border_style: str = "dim") -> Panel:
    """Render a single deck's card list as a Rich Panel.

    Args:
        deck_name: Name of the deck to display as title
        cards: Dictionary of {card_name: quantity}
        border_style: Style for the panel border

    Returns:
        Rich Panel containing the decklist table
    """
    if not cards:
        return Panel(
            "[italic dim](empty deck)[/italic dim]",
            title=f"[bold bright_cyan]{escape(deck_name)}[/bold bright_cyan]",
            border_style=border_style,
        )

    total_cards = sum(cards.values())
    card_items = sorted(cards.items(), key=lambda x: x[0])
    inner_table = card_table([(name, qty) for name, qty in card_items])

    return Panel(
        inner_table,
        title=f"[bold bright_cyan]{escape(deck_name)}[/bold bright_cyan] ({total_cards} cards)",
        border_style=border_style,
    )


def render_multiple_decks(decks: list[tuple[str, dict[str, int]]]) -> None:
    """Render multiple decklists side-by-side using Rich panels.

    Args:
        decks: List of (deck_name, cards_dict) tuples
    """
    if not decks:
        return

    deck_panels: list[Panel] = []
    for deck_name, cards in decks:
        deck_panels.append(render_decklist(deck_name, cards))

    # Render panels in rows of 2
    for i in range(0, len(deck_panels), 2):
        chunk = deck_panels[i : i + 2]
        if len(chunk) == 2:
            console.print(side_by_side(chunk[0], chunk[1]))
        else:
            console.print(chunk[0])
