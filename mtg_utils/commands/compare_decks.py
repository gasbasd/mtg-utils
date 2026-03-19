import click
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from mtg_utils.utils.console import console
from mtg_utils.utils.readers import read_list


def _card_table(cards: list[tuple[str, int]], row_style: str = "") -> Table:
    table = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    table.add_column("qty", justify="right", style="dim")
    table.add_column("name", style=row_style)
    for card, qty in sorted(cards, key=lambda x: x[0]):
        table.add_row(str(qty), escape(card))
    return table


@click.command()
@click.option("--deck1-file", "-d1", help="Path to the deck 1 file")
@click.option("--deck2-file", "-d2", help="Path to the deck 2 file")
def compare_decks(deck1_file: str, deck2_file: str) -> None:
    """Compare two specified decks."""
    deck1 = {}
    for card in read_list(deck1_file):
        parts = card.split(" ", 1)
        if len(parts) == 2:
            quantity, name = parts
            deck1[name] = int(quantity)

    deck2 = {}
    for card in read_list(deck2_file):
        parts = card.split(" ", 1)
        if len(parts) == 2:
            quantity, name = parts
            deck2[name] = int(quantity)

    all_cards = set(deck1.keys()) | set(deck2.keys())
    common_cards = []
    unique_to_deck1 = []
    unique_to_deck2 = []

    for card in all_cards:
        qty1 = deck1.get(card, 0)
        qty2 = deck2.get(card, 0)
        if qty1 > 0 and qty2 > 0:
            common_qty = min(qty1, qty2)
            common_cards.append((card, common_qty))
            if qty1 > common_qty:
                unique_to_deck1.append((card, qty1 - common_qty))
            if qty2 > common_qty:
                unique_to_deck2.append((card, qty2 - common_qty))
        elif qty1 > 0:
            unique_to_deck1.append((card, qty1))
        else:
            unique_to_deck2.append((card, qty2))

    total_common_qty = sum(qty for _, qty in common_cards)
    total_unique_to_deck1_qty = sum(qty for _, qty in unique_to_deck1)
    total_unique_to_deck2_qty = sum(qty for _, qty in unique_to_deck2)

    if common_cards:
        console.print(
            Panel(
                _card_table(common_cards),
                title=f"Cards in common: {total_common_qty} ({len(common_cards)} unique)",
                border_style="white",
            )
        )
    if unique_to_deck1:
        console.print(
            Panel(
                _card_table(unique_to_deck1, row_style="cyan"),
                title=f"Only in {escape(deck1_file)}: {total_unique_to_deck1_qty} ({len(unique_to_deck1)} unique)",
                border_style="cyan",
            )
        )
    if unique_to_deck2:
        console.print(
            Panel(
                _card_table(unique_to_deck2, row_style="magenta"),
                title=f"Only in {escape(deck2_file)}: {total_unique_to_deck2_qty} ({len(unique_to_deck2)} unique)",
                border_style="magenta",
            )
        )
