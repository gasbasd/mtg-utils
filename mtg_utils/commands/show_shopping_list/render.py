from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from mtg_utils.utils.console import console
from mtg_utils.utils.panels import side_by_side

_DECK_COLORS = [
    "cyan",
    "yellow",
    "magenta",
    "bright_cyan",
    "bright_yellow",
    "bright_magenta",
    "blue",
    "bright_blue",
]


def render_shopping_list(
    to_buy: list[tuple[str, int, list[str], list[str]]],
    already_available: list[tuple[str, int]],
    num_sources: int,
    purchased_names: set[str] | None = None,
) -> None:
    if purchased_names is None:
        purchased_names = set()
    total_to_buy = sum(qty for _, qty, _, __ in to_buy)
    unique_to_buy = len(to_buy)
    console.print(
        Rule(
            f"[bold]Shopping list: {num_sources} deck(s) · {total_to_buy} cards to buy ({unique_to_buy} unique)[/bold]"
        )
    )

    if to_buy:
        all_labels: list[str] = sorted(
            {lbl for _, _, src, cfg in to_buy for lbl in src + cfg}
        )
        deck_color: dict[str, str] = {
            lbl: _DECK_COLORS[i % len(_DECK_COLORS)] for i, lbl in enumerate(all_labels)
        }

        def fmt_labels(labels: list[str]) -> str:
            return ", ".join(f"[{deck_color[lab]}]{escape(lab)}[/]" for lab in labels)

        tbl = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
        tbl.add_column("qty", justify="right", style="dim")
        tbl.add_column("name", style="red")
        tbl.add_column("requested by", style="dim")
        tbl.add_column("in decks", style="dim")
        for card_name, qty, source_labels, config_deck_names in to_buy:
            tbl.add_row(
                str(qty),
                escape(card_name),
                fmt_labels(source_labels),
                fmt_labels(config_deck_names),
            )
        buy_panel: Panel = Panel(
            tbl,
            title=f"Need to buy: {total_to_buy} ({unique_to_buy} unique)",
            border_style="red",
        )
    else:
        buy_panel = Panel("[green]✓ Nothing to buy![/green]", border_style="green")

    if already_available:
        total_avail_qty = sum(qty for _, qty in already_available)
        avail_tbl = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
        avail_tbl.add_column("p", no_wrap=True)
        avail_tbl.add_column("qty", justify="right", style="dim")
        avail_tbl.add_column("name")
        for name, qty in already_available:
            marker = "[bold]*[/bold]" if name in purchased_names else ""
            avail_tbl.add_row(marker, str(qty), escape(name))
        avail_panel: Panel | None = Panel(
            avail_tbl,
            title=f"Already available: {total_avail_qty} ({len(already_available)} unique)",
            border_style="green",
        )
    else:
        avail_panel = None

    if avail_panel:
        console.print(side_by_side(buy_panel, avail_panel))
    else:
        console.print(buy_panel)
