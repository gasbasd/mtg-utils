import click
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule

from mtg_utils.utils.cards import parse_card_list
from mtg_utils.utils.console import console
from mtg_utils.utils.panels import card_table, side_by_side
from mtg_utils.utils.readers import read_list


@click.command()
@click.option("--deck1-file", "-d1", help="Path to the deck 1 file")
@click.option("--deck2-file", "-d2", help="Path to the deck 2 file")
def compare_decks(deck1_file: str, deck2_file: str) -> None:
    """Compare two specified decks."""
    deck1 = parse_card_list(read_list(deck1_file))
    deck2 = parse_card_list(read_list(deck2_file))

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

    console.print(Rule(f"[bold]{escape(deck1_file)} vs {escape(deck2_file)}[/bold]"))

    if common_cards:
        console.print(
            Panel(
                card_table(common_cards),
                title=f"Cards in common: {total_common_qty} ({len(common_cards)} unique)",
                border_style="white",
            )
        )

    if unique_to_deck1 and unique_to_deck2:
        panel1 = Panel(
            card_table(unique_to_deck1, row_style="cyan"),
            title=f"Only in {escape(deck1_file)}: {total_unique_to_deck1_qty} ({len(unique_to_deck1)} unique)",
            border_style="cyan",
        )
        panel2 = Panel(
            card_table(unique_to_deck2, row_style="magenta"),
            title=f"Only in {escape(deck2_file)}: {total_unique_to_deck2_qty} ({len(unique_to_deck2)} unique)",
            border_style="magenta",
        )
        console.print(side_by_side(panel1, panel2))
    elif unique_to_deck1:
        console.print(
            Panel(
                card_table(unique_to_deck1, row_style="cyan"),
                title=f"Only in {escape(deck1_file)}: {total_unique_to_deck1_qty} ({len(unique_to_deck1)} unique)",
                border_style="cyan",
            )
        )
    elif unique_to_deck2:
        console.print(
            Panel(
                card_table(unique_to_deck2, row_style="magenta"),
                title=f"Only in {escape(deck2_file)}: {total_unique_to_deck2_qty} ({len(unique_to_deck2)} unique)",
                border_style="magenta",
            )
        )
