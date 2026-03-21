import os
from collections import Counter

import click
from rich.console import Group, RenderableType
from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config
from mtg_utils.utils.console import console, err_console
from mtg_utils.utils.moxfield_api import get_deck_list, get_library, library_sort_key
from mtg_utils.utils.readers import read_list


def _update_owned_cards(binder_id) -> list[str]:
    owned_cards = get_library(binder_id=binder_id)

    # Ensure directory exists
    os.makedirs("card_library", exist_ok=True)

    with open("card_library/owned_cards.txt", "w") as file:
        for card in owned_cards:
            file.write(f"{card}\n")
    console.print("[green]✓[/green] Updated owned cards: card_library/owned_cards.txt")
    return owned_cards


def _process_purchased_cards(config) -> list[str]:
    purchased_file = config.get("purchased_file", "card_library/purchased.txt")

    # Check if purchased.txt exists
    if not os.path.exists(path=purchased_file):
        console.print(f"[green]✓[/green] Creating empty purchased cards file at {escape(purchased_file)}")
        # Ensure directory exists
        os.makedirs(os.path.dirname(purchased_file), exist_ok=True)
        # Create empty file
        with open(purchased_file, "w") as file:
            pass
        return []

    raw_cards = read_list(purchased_file)
    card_counter = Counter(raw_cards)
    purchased_cards = [f"{quantity} {card}" for card, quantity in card_counter.items()]

    purchased_formatted_file = config.get("purchased_formatted_file", "card_library/purchased_formatted.txt")
    with open(file=purchased_formatted_file, mode="w") as file:
        for card in sorted(purchased_cards):
            file.write(f"{card}\n")

    console.print(
        f"[green]✓[/green] Processed purchased cards: {len(purchased_cards)} unique cards from {len(raw_cards)} total entries"
    )
    return purchased_cards


def _calculate_available_cards(library: list[str], decks: list[tuple[str, list[str], dict]], config: dict) -> list[str]:
    """Calculate available cards by subtracting deck cards from the library.

    Supports shared_decks: if a deck has a 'shared_decks' list in its config, it will reuse cards from those
    decks without consuming additional cards from the library pool. Only the remainder is consumed.
    """
    # Load purchased card names for * marker in warnings
    purchased_names: set[str] = set()
    purchased_file = config.get("purchased_formatted_file", "")
    if purchased_file:
        try:
            for entry in read_list(purchased_file):
                purchased_names.add(entry.split(" ", 1)[1])
        except FileNotFoundError:
            pass

    # Convert library to dictionary
    library_dict = {}
    for card_entry in library:
        parts = card_entry.split(" ", 1)
        quantity = int(parts[0])
        card_name = parts[1]
        library_dict[card_name] = quantity

    # Build deck lookup dictionary for card quantities
    deck_cards = {}  # deck_name -> {card_name: quantity}
    for deck_name, deck, deck_config in decks:
        deck_cards[deck_name] = {}
        for card_entry in deck:
            parts = card_entry.split(" ", 1)
            quantity = int(parts[0])
            card_name = parts[1]
            deck_cards[deck_name][card_name] = quantity

    # Calculate used cards across decks and check for unavailable cards
    used_cards = {}
    card_usage_by_deck = {}  # Track which decks use which cards
    unavailable_cards = {}
    deck_configs = {}  # Store deck configs for later reference
    truly_shared = {}  # deck_name -> set of card names genuinely shared (library insufficient without sharing)

    for deck_name, deck, deck_config in decks:
        deck_configs[deck_name] = deck_config
        truly_shared[deck_name] = set()
        deck_unavailable = []
        shared_decks = deck_config.get("shared_decks", [])

        # Validate shared_decks
        for shared_deck_name in shared_decks:
            if shared_deck_name not in deck_cards:
                err_console.print(
                    f"[yellow]⚠[/yellow] WARNING: Deck '{escape(deck_name)}' references non-existent shared deck '{escape(shared_deck_name)}'"
                )

        for card_entry in deck:
            parts = card_entry.split(" ", 1)
            quantity = int(parts[0])
            card_name = parts[1]

            # Calculate how many cards can be shared from shared_decks
            shared_quantity = 0
            shared_details = []  # Track which decks provide which quantities
            for shared_deck_name in shared_decks:
                if shared_deck_name in deck_cards:
                    deck_has = deck_cards[shared_deck_name].get(card_name, 0)
                    if deck_has > 0:
                        shared_details.append(f"{deck_has} in {shared_deck_name}")
                    shared_quantity += deck_has

            # Only consume the difference from the library pool
            quantity_to_consume = max(0, quantity - shared_quantity)

            # Check if card is available in library considering cumulative usage
            total_in_library = library_dict.get(card_name, 0)
            already_used = used_cards.get(card_name, 0)
            available_quantity = total_in_library - already_used

            # Track cards that genuinely need sharing (library can't cover without it)
            if shared_quantity > 0 and available_quantity < quantity:
                truly_shared[deck_name].add(card_name)

            if available_quantity < quantity_to_consume:
                msg = f"{quantity} {card_name} (have {total_in_library}"
                if shared_details:
                    msg += f", sharing: {', '.join(shared_details)}"
                if already_used > 0 and card_name in card_usage_by_deck:
                    decks_using = ", ".join([f"{q} in {dn}" for dn, q in card_usage_by_deck[card_name].items()])
                    msg += f", already used: {decks_using}"
                msg += ")"
                deck_unavailable.append((card_name, msg))

            # Track used cards (only the quantity consumed from library)
            if quantity_to_consume > 0:
                if card_name in used_cards:
                    used_cards[card_name] += quantity_to_consume
                else:
                    used_cards[card_name] = quantity_to_consume

                # Track which deck uses this card
                if card_name not in card_usage_by_deck:
                    card_usage_by_deck[card_name] = {}
                card_usage_by_deck[card_name][deck_name] = quantity_to_consume

        if deck_unavailable:
            unavailable_cards[deck_name] = deck_unavailable

    # Print warnings for unavailable cards
    if unavailable_cards:
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

    # Show shared decks information for all decks that have shared_decks configured
    decks_with_sharing = [(name, cfg) for name, cfg in deck_configs.items() if cfg.get("shared_decks")]
    if decks_with_sharing:
        # Each entry: (renderable, title, content_lines) — panels are built later for equal heights
        deck_panel_specs: list[tuple[RenderableType, str, int]] = []

        for deck_name, deck_config in decks_with_sharing:
            shared_decks = deck_config.get("shared_decks", [])
            current_deck_cards = deck_cards[deck_name]

            # Collect all shared cards from all shared decks
            shared_cards_info = {}  # card_name -> list of (shared_deck_name, quantity_in_shared_deck)
            for shared_deck_name in shared_decks:
                if shared_deck_name in deck_cards:
                    for card_name in current_deck_cards.keys():
                        if card_name in deck_cards[shared_deck_name]:
                            if card_name not in shared_cards_info:
                                shared_cards_info[card_name] = []
                            shared_cards_info[card_name].append(
                                (shared_deck_name, deck_cards[shared_deck_name][card_name])
                            )

            def _shared_card_table(card_names: list[str]) -> Table:
                tbl = Table(box=None, show_header=False, padding=(0, 1, 0, 0))
                tbl.add_column("qty", justify="right", style="dim")
                tbl.add_column("name")
                for card_name in sorted(card_names):
                    qty = current_deck_cards[card_name]
                    tbl.add_row(str(qty), escape(card_name))
                return tbl

            if len(shared_decks) > 1:
                # Cards common across multiple shared decks vs exclusive to one
                common_shared_cards = {card: dl for card, dl in shared_cards_info.items() if len(dl) > 1}
                exclusive_shared_cards = {card: dl for card, dl in shared_cards_info.items() if len(dl) == 1}

                # Build sub-panel specs: (title, renderable, row_count)
                sub_panel_specs: list[tuple[str, RenderableType, int]] = []

                if common_shared_cards:
                    common_count = sum(current_deck_cards[c] for c in common_shared_cards)
                    common_cards_list = list(common_shared_cards.keys())
                    sub_panel_specs.append(
                        (
                            f"[bold yellow1]Common across shared decks ({common_count} cards)[/bold yellow1]",
                            _shared_card_table(common_cards_list),
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
                                _shared_card_table(exclusive_cards),
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
                # outer content height = the inner sub-panels' height
                deck_panel_specs.append(
                    (inner_grid, f"[bold bright_cyan]{escape(deck_name)}[/bold bright_cyan]", sub_height)
                )
            else:
                # Single shared deck — wrap in inner panel titled with shared deck name
                shared_deck_name = shared_decks[0]
                card_tbl = _shared_card_table(list(shared_cards_info.keys()))
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
                grid = Table.grid(expand=True)
                grid.add_column(ratio=1)
                grid.add_column(ratio=1)
                grid.add_row(panel0, panel1)
                console.print(grid)
            else:
                height = chunk[0][2] + 2
                console.print(Panel(chunk[0][0], title=chunk[0][1], border_style="dim", height=height))

    # Calculate available cards
    available_dict = {}
    for card_name, quantity in library_dict.items():
        used_quantity = used_cards.get(card_name, 0)
        available = quantity - used_quantity
        if available > 0:
            available_dict[card_name] = available

    # Convert back to the required string format and sort
    available_cards = [f"{quantity} {name}" for name, quantity in available_dict.items()]
    available_cards.sort(key=library_sort_key)

    with open("card_library/available_cards.txt", "w") as file:
        for card in available_cards:
            file.write(f"{card}\n")
    console.print("[green]✓[/green] Updated available cards: card_library/available_cards.txt")
    return available_cards


@click.command()
@click.option("--config-file", help="Path to the config file", default=DEFAULT_CONFIG_FILE)
def update_card_library(config_file) -> None:
    """Update the card library with built decks and owned cards."""

    config = load_config(config_file=config_file)

    # Fetch all decks with a progress spinner
    results = []
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console, transient=True) as progress:
        for deck_name, deck_info in config["decks"].items():
            task = progress.add_task(f"Fetching [bold]{escape(deck_name)}[/bold]\u2026", total=None)
            deck = get_deck_list(deck_info["id"])
            progress.remove_task(task)
            if deck:
                os.makedirs(os.path.dirname(deck_info["file"]), exist_ok=True)
                with open(deck_info["file"], mode="w") as file:
                    for card in deck:
                        file.write(f"{card}\n")
                results.append((deck_name, True, deck_info["file"], deck, deck_info))
            else:
                err_console.print(
                    f"[yellow]⚠[/yellow] Failed to retrieve [bold]{escape(deck_name)}[/bold] deck from Moxfield."
                )
                results.append((deck_name, False, "\u2014", [], deck_info))

    # Print summary table
    tbl = Table(box=None, show_header=True, header_style="bold")
    tbl.add_column("Deck")
    tbl.add_column("Status")
    tbl.add_column("File")
    for name, ok, path, _, _ in results:
        tbl.add_row(name, "[green]✓[/green]" if ok else "[red]✗ failed[/red]", path)
    console.print(Panel(tbl, title="Deck sync", border_style="blue"))

    # Build structured deck data for downstream use
    decks = [(name, deck, info) for name, ok, _, deck, info in results if ok]

    owned_cards = _update_owned_cards(binder_id=config["binder_id"])
    _process_purchased_cards(config=config)

    _calculate_available_cards(owned_cards, decks, config)
