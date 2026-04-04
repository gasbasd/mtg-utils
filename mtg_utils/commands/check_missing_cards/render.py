from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from mtg_utils.utils.console import console
from mtg_utils.utils.panels import panel_row, side_by_side


def render_results(
    available_in_deck: list[str],
    completely_missing_cards: list[tuple[str, int]],
    partially_missing_cards: list[tuple[str, int, str]],
    cards_by_deck: dict[str, list[tuple[str, int, int]]],
    purchased_names: set[str],
    owned_dict: dict[str, int],
    total: int,
) -> None:
    console.print(Rule(f"[bold]Total cards in deck: {total}[/bold]"))

    total_available_qty = sum(int(card.split(" ", 1)[0]) for card in available_in_deck)
    if available_in_deck:
        tbl = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
        tbl.add_column("p", no_wrap=True)
        tbl.add_column("qty", justify="right", style="dim")
        tbl.add_column("name")
        for entry in sorted(available_in_deck):
            qty, name = entry.split(" ", 1)
            marker = "[bold]*[/bold]" if name in purchased_names and owned_dict.get(name, 0) < int(qty) else ""
            tbl.add_row(marker, qty, escape(name))
        avail_panel = Panel(
            tbl,
            title=f"Available: {total_available_qty} ({len(available_in_deck)} unique)",
            border_style="green",
        )
    else:
        avail_panel = None

    total_completely_missing = sum(qty for _, qty in completely_missing_cards)
    if completely_missing_cards:
        tbl = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
        tbl.add_column("qty", justify="right", style="dim")
        tbl.add_column("name", style="red")
        for card_name, missing_qty in sorted(completely_missing_cards, key=lambda x: x[0]):
            tbl.add_row(str(missing_qty), escape(card_name))
        missing_panel = Panel(
            tbl,
            title=f"Missing: {total_completely_missing} ({len(completely_missing_cards)} unique)",
            border_style="red",
        )
    else:
        missing_panel = Panel("[green]✓ All cards available![/green]", border_style="green")

    if avail_panel:
        console.print(side_by_side(avail_panel, missing_panel))
    else:
        console.print(missing_panel)

    if partially_missing_cards:
        total_from_others = sum(qty for _, qty, _ in partially_missing_cards)
        tbl = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
        tbl.add_column("qty", justify="right", style="dim")
        tbl.add_column("name")
        tbl.add_column("decks", style="dim")
        for card_name, qty, deck_info in sorted(partially_missing_cards, key=lambda x: x[0]):
            tbl.add_row(str(qty), escape(card_name), escape(f"[{deck_info}]"))
        console.print(
            Panel(
                tbl,
                title=f"In other decks: {total_from_others} ({len(partially_missing_cards)} unique)",
                border_style="yellow",
            )
        )

        deck_items = sorted(cards_by_deck.items())
        for i in range(0, len(deck_items), 3):
            row_decks = deck_items[i : i + 3]
            row_panels = []
            for deck_name, cards in row_decks:
                total_needed = sum(usable_qty for _, _, usable_qty in cards if usable_qty > 0)
                tbl = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
                tbl.add_column("p", no_wrap=True)
                tbl.add_column("qty", justify="right", style="dim")
                tbl.add_column("name")
                for card_name, total_qty, usable_qty in sorted(cards, key=lambda x: x[0]):
                    if usable_qty > 0:
                        marker = "[bold]*[/bold]" if card_name in purchased_names else ""
                        tbl.add_row(marker, str(usable_qty), escape(card_name))
                row_panels.append(
                    Panel(
                        tbl,
                        title=f"{escape(deck_name)} — {total_needed} cards needed",
                        border_style="dim",
                    )
                )
            console.print(panel_row(row_panels))
