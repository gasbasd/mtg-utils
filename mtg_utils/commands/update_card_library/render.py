from rich.console import Group, RenderableType
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mtg_utils.utils.config import DeckConfig
from mtg_utils.utils.console import console, err_console
from mtg_utils.utils.panels import side_by_side


def _shared_card_table(card_names: list[str], deck_cards_for_current: dict[str, int]) -> Table:
    tbl = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
    tbl.add_column("qty", justify="right", style="dim")
    tbl.add_column("name")
    for card_name in sorted(card_names):
        tbl.add_row(str(deck_cards_for_current[card_name]), escape(card_name))
    return tbl


def _render_unavailable_warnings(
    unavailable_cards: dict[str, list[tuple[str, str]]],
    purchased_names: set[str],
) -> None:
    if not unavailable_cards:
        return
    warn_parts: list = []
    for deck_name, cards in unavailable_cards.items():
        deck_tbl = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
        deck_tbl.add_column("marker", no_wrap=True)
        deck_tbl.add_column("card_name")
        deck_tbl.add_column("detail", style="dim")
        for card_name, msg in cards:
            marker = "[bold]*[/bold]" if card_name in purchased_names else ""
            qty_name, _, detail = msg.partition(" (")
            detail = f"({detail}" if detail else ""
            deck_tbl.add_row(marker, escape(qty_name), escape(detail))
        warn_parts.append(Text.from_markup(f"[bold]{escape(deck_name)}[/bold] deck is missing:"))
        warn_parts.append(deck_tbl)
    err_console.print(Panel(Group(*warn_parts), title="⚠ WARNING: Unavailable cards", border_style="yellow"))


def _render_shared_deck_panels(
    deck_cards: dict[str, dict[str, int]],
    deck_configs: dict[str, DeckConfig],
) -> None:
    decks_with_sharing = [(name, cfg) for name, cfg in deck_configs.items() if cfg.shared_decks]
    if not decks_with_sharing:
        return

    deck_panel_specs: list[tuple[RenderableType, str, int]] = []

    for deck_name, deck_config in decks_with_sharing:
        shared_decks: list[str] = deck_config.shared_decks
        current_deck_cards = deck_cards[deck_name]

        shared_cards_info: dict[str, list[tuple[str, int]]] = {}
        for shared_deck_name in shared_decks:
            if shared_deck_name in deck_cards:
                for card_name in current_deck_cards:
                    if card_name in deck_cards[shared_deck_name]:
                        shared_cards_info.setdefault(card_name, []).append(
                            (shared_deck_name, deck_cards[shared_deck_name][card_name])
                        )

        if len(shared_decks) > 1:
            common_shared_cards = {card: dl for card, dl in shared_cards_info.items() if len(dl) > 1}
            exclusive_shared_cards = {card: dl for card, dl in shared_cards_info.items() if len(dl) == 1}

            sub_panel_specs: list[tuple[str, RenderableType, int]] = []

            if common_shared_cards:
                common_count = sum(current_deck_cards[c] for c in common_shared_cards)
                common_cards_list = list(common_shared_cards.keys())
                sub_panel_specs.append(
                    (
                        f"[bold yellow1]Common across shared decks ({common_count} cards)[/bold yellow1]",
                        _shared_card_table(common_cards_list, current_deck_cards),
                        len(common_cards_list),
                    )
                )

            for shared_deck_name in shared_decks:
                if shared_deck_name not in deck_cards:
                    continue
                exclusive_cards = [
                    c
                    for c in sorted(current_deck_cards)
                    if c in exclusive_shared_cards
                    and len(shared_cards_info[c]) == 1
                    and shared_cards_info[c][0][0] == shared_deck_name
                ]
                if exclusive_cards:
                    sub_panel_specs.append(
                        (
                            f"[bold yellow1]{escape(shared_deck_name)} ({len(exclusive_cards)} cards)[/bold yellow1]",
                            _shared_card_table(exclusive_cards, current_deck_cards),
                            len(exclusive_cards),
                        )
                    )
                else:
                    sub_panel_specs.append(
                        (
                            f"[bold yellow1]{escape(shared_deck_name)} (0 cards)[/bold yellow1]",
                            Text("(no exclusive cards)"),
                            1,
                        )
                    )

            sub_height = max(spec[2] for spec in sub_panel_specs) + 2
            inner_grid = Table.grid(expand=True)
            for _ in sub_panel_specs:
                inner_grid.add_column(ratio=1)
            inner_grid.add_row(
                *[
                    Panel(renderable, title=title, border_style="dim", height=sub_height)
                    for title, renderable, _ in sub_panel_specs
                ]
            )
            deck_panel_specs.append(
                (inner_grid, f"[bold bright_cyan]{escape(deck_name)}[/bold bright_cyan]", sub_height)
            )
        else:
            shared_deck_name = shared_decks[0]
            card_tbl = _shared_card_table(list(shared_cards_info.keys()), current_deck_cards)
            inner_panel = Panel(
                card_tbl,
                title=f"[bold yellow1]{escape(shared_deck_name)} ({len(shared_cards_info)} cards)[/bold yellow1]",
                border_style="dim",
            )
            deck_panel_specs.append(
                (
                    inner_panel,
                    f"[bold bright_cyan]{escape(deck_name)}[/bold bright_cyan]",
                    len(shared_cards_info) + 2,
                )
            )

    for i in range(0, len(deck_panel_specs), 2):
        chunk = deck_panel_specs[i : i + 2]
        if len(chunk) == 2:
            height = max(chunk[0][2], chunk[1][2]) + 2
            panel0 = Panel(chunk[0][0], title=chunk[0][1], border_style="dim", height=height)
            panel1 = Panel(chunk[1][0], title=chunk[1][1], border_style="dim", height=height)
            console.print(side_by_side(panel0, panel1))
        else:
            height = chunk[0][2] + 2
            console.print(Panel(chunk[0][0], title=chunk[0][1], border_style="dim", height=height))
