from rich.console import Group, RenderableType
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mtg_utils.commands.update_card_library.logic import DeckFetchResult
from mtg_utils.utils.config import DeckConfig
from mtg_utils.utils.console import console, err_console
from mtg_utils.utils.panels import card_table, panel_row, side_by_side


def render_unavailable_warnings(
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


def render_shared_deck_panels(
    deck_cards: dict[str, dict[str, int]],
    deck_configs: dict[str, DeckConfig],
) -> None:
    deck_panel_specs: list[tuple[RenderableType, str]] = []

    for deck_name, deck_config in deck_configs.items():
        current_deck_cards = deck_cards[deck_name]
        shared_decks: list[str] = deck_config.shared_decks

        if not shared_decks:
            all_cards_list = sorted(current_deck_cards.keys())
            all_count = sum(current_deck_cards[c] for c in all_cards_list)
            inner_grid = panel_row(
                [
                    Panel(
                        card_table([(name, current_deck_cards[name]) for name in all_cards_list]),
                        title=f"[bold yellow1]All cards ({all_count} cards)[/bold yellow1]",
                        border_style="dim",
                    )
                ]
            )
            deck_panel_specs.append((inner_grid, f"[bold bright_cyan]{escape(deck_name)}[/bold bright_cyan]"))
            continue

        sub_panel_specs: list[tuple[str, RenderableType]] = []

        if len(shared_decks) > 1:
            shared_deck_order = {name: idx for idx, name in enumerate(shared_decks)}
            valid_shared_decks = [name for name in shared_decks if name in deck_cards]
            common_quantities: dict[str, int] = {}
            shared_panel_quantities: dict[str, dict[str, int]] = {name: {} for name in valid_shared_decks}
            only_in_deck_quantities: dict[str, int] = {}

            for card_name, current_qty in current_deck_cards.items():
                overlaps: list[tuple[str, int]] = []
                for shared_deck_name in valid_shared_decks:
                    shared_qty = deck_cards[shared_deck_name].get(card_name)
                    if shared_qty is None:
                        continue
                    overlaps.append((shared_deck_name, min(current_qty, shared_qty)))

                if not overlaps:
                    only_in_deck_quantities[card_name] = only_in_deck_quantities.get(card_name, 0) + current_qty
                    continue

                if len(overlaps) == 1:
                    shared_deck_name, overlap_qty = overlaps[0]
                    if overlap_qty > 0:
                        shared_panel_quantities[shared_deck_name][card_name] = (
                            shared_panel_quantities[shared_deck_name].get(card_name, 0) + overlap_qty
                        )
                    continue

                common_qty = min(overlap_qty for _, overlap_qty in overlaps)
                if common_qty > 0:
                    common_quantities[card_name] = common_quantities.get(card_name, 0) + common_qty

                max_overlap_deck, max_overlap = max(
                    overlaps,
                    key=lambda pair: (pair[1], -shared_deck_order[pair[0]]),
                )
                shared_residual_qty = max(0, max_overlap - common_qty)
                if shared_residual_qty > 0:
                    shared_panel_quantities[max_overlap_deck][card_name] = (
                        shared_panel_quantities[max_overlap_deck].get(card_name, 0) + shared_residual_qty
                    )

                only_in_current_residual = max(0, current_qty - max_overlap)
                if only_in_current_residual > 0:
                    only_in_deck_quantities[card_name] = (
                        only_in_deck_quantities.get(card_name, 0) + only_in_current_residual
                    )

            if common_quantities:
                common_rendered_cards = [
                    (card_name, common_quantities[card_name]) for card_name in sorted(common_quantities)
                ]
                common_count = sum(common_quantities.values())
                sub_panel_specs.append(
                    (
                        f"[bold yellow1]Common across shared decks ({common_count} cards)[/bold yellow1]",
                        card_table(common_rendered_cards),
                    )
                )

            for shared_deck_name in valid_shared_decks:
                shared_quantities = shared_panel_quantities[shared_deck_name]
                if shared_quantities:
                    shared_rendered_cards = [
                        (card_name, shared_quantities[card_name]) for card_name in sorted(shared_quantities)
                    ]
                    shared_total = sum(shared_quantities.values())
                    sub_panel_specs.append(
                        (
                            f"[bold yellow1]{escape(shared_deck_name)} ({shared_total} cards)[/bold yellow1]",
                            card_table(shared_rendered_cards),
                        )
                    )
                else:
                    sub_panel_specs.append(
                        (
                            f"[bold yellow1]{escape(shared_deck_name)} (0 cards)[/bold yellow1]",
                            Text("(no exclusive cards)"),
                        )
                    )

            only_in_deck_cards = sorted(only_in_deck_quantities)
            only_in_deck_total = sum(only_in_deck_quantities.values())
            if only_in_deck_cards:
                sub_panel_specs.append(
                    (
                        f"[bold yellow1]Only in {escape(deck_name)} ({only_in_deck_total} cards)[/bold yellow1]",
                        card_table([(name, only_in_deck_quantities[name]) for name in only_in_deck_cards]),
                    )
                )
            else:
                sub_panel_specs.append(
                    (
                        f"[bold yellow1]Only in {escape(deck_name)} (0 cards)[/bold yellow1]",
                        Text("(no exclusive cards)"),
                    )
                )
        else:
            shared_deck_name = shared_decks[0]
            shared_cards_info: dict[str, int] = {}
            if shared_deck_name in deck_cards:
                for card_name in current_deck_cards:
                    if card_name in deck_cards[shared_deck_name]:
                        shared_cards_info[card_name] = min(
                            current_deck_cards[card_name], deck_cards[shared_deck_name][card_name]
                        )

            shared_cards_list = sorted(shared_cards_info.keys())
            if shared_cards_list:
                shared_rendered_cards = [(card_name, shared_cards_info[card_name]) for card_name in shared_cards_list]
                shared_total = sum(quantity for _, quantity in shared_rendered_cards)
                sub_panel_specs.append(
                    (
                        f"[bold yellow1]{escape(shared_deck_name)} ({shared_total} cards)[/bold yellow1]",
                        card_table(shared_rendered_cards),
                    )
                )
            else:
                sub_panel_specs.append(
                    (
                        f"[bold yellow1]{escape(shared_deck_name)} (0 cards)[/bold yellow1]",
                        Text("(no exclusive cards)"),
                    )
                )

            only_in_deck_cards = sorted(c for c in current_deck_cards if c not in shared_cards_info)
            if only_in_deck_cards:
                only_in_deck_total = sum(current_deck_cards[c] for c in only_in_deck_cards)
                sub_panel_specs.append(
                    (
                        f"[bold yellow1]Only in {escape(deck_name)} ({only_in_deck_total} cards)[/bold yellow1]",
                        card_table([(name, current_deck_cards[name]) for name in only_in_deck_cards]),
                    )
                )
            else:
                sub_panel_specs.append(
                    (
                        f"[bold yellow1]Only in {escape(deck_name)} (0 cards)[/bold yellow1]",
                        Text("(no exclusive cards)"),
                    )
                )

        rows = []
        for j in range(0, len(sub_panel_specs), 2):
            row_chunk = sub_panel_specs[j : j + 2]
            rows.append(
                panel_row([Panel(renderable, title=title, border_style="dim") for title, renderable in row_chunk])
            )
        inner_grid = Group(*rows)
        deck_panel_specs.append((inner_grid, f"[bold bright_cyan]{escape(deck_name)}[/bold bright_cyan]"))

    for i in range(0, len(deck_panel_specs), 2):
        chunk = deck_panel_specs[i : i + 2]
        if len(chunk) == 2:
            panel0 = Panel(chunk[0][0], title=chunk[0][1], border_style="dim")
            panel1 = Panel(chunk[1][0], title=chunk[1][1], border_style="dim")
            console.print(side_by_side(panel0, panel1))
        else:
            console.print(Panel(chunk[0][0], title=chunk[0][1], border_style="dim"))


def render_failed_deck_warning(deck_name: str) -> None:
    err_console.print(f"[yellow]⚠[/yellow] Failed to retrieve [bold]{escape(deck_name)}[/bold] deck from Moxfield.")


def render_deck_sync_panel(results: list[DeckFetchResult]) -> None:
    tbl = Table(box=None, show_header=True, header_style="bold")
    tbl.add_column("Deck")
    tbl.add_column("Status")
    tbl.add_column("File")
    for r in results:
        tbl.add_row(r.name, "[green]✓[/green]" if r.ok else "[red]✗ failed[/red]", r.file)
    console.print(Panel(tbl, title="Deck sync", border_style="blue"))
