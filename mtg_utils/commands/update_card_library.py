import os
from collections import Counter

import click
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

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
        err_console.print(
            "[yellow]⚠[/yellow] WARNING: Some cards in decks are not available in the available cards:",
        )
        for deck_name, cards in unavailable_cards.items():
            err_console.print(f"\n  {escape(deck_name)} deck is missing:")
            for card_name, msg in cards:
                marker = "[bold]*[/bold] " if card_name in purchased_names else ""
                err_console.print(f"    - {marker}{escape(msg)}")

    # Show shared decks information for all decks that have shared_decks configured
    decks_with_sharing = [(name, cfg) for name, cfg in deck_configs.items() if cfg.get("shared_decks")]
    if decks_with_sharing:
        console.print("\nShared decks configuration:")
        for deck_name, deck_config in decks_with_sharing:
            shared_decks = deck_config.get("shared_decks", [])
            current_deck_cards = deck_cards[deck_name]

            # Collect all shared cards from all shared decks
            shared_cards_info = {}  # card_name -> list of (shared_deck_name, quantity_in_shared_deck)
            for shared_deck_name in shared_decks:
                if shared_deck_name in deck_cards:
                    shared_deck_cards = deck_cards[shared_deck_name]
                    for card_name in current_deck_cards.keys():
                        if card_name in shared_deck_cards:
                            if card_name not in shared_cards_info:
                                shared_cards_info[card_name] = []
                            shared_cards_info[card_name].append((shared_deck_name, shared_deck_cards[card_name]))

            # If multiple shared decks, separate exclusive cards from common cards
            if len(shared_decks) > 1:
                # Cards in multiple shared decks (common)
                common_shared_cards = {
                    card: decks_list for card, decks_list in shared_cards_info.items() if len(decks_list) > 1
                }
                # Cards in only one shared deck (exclusive)
                exclusive_shared_cards = {
                    card: decks_list for card, decks_list in shared_cards_info.items() if len(decks_list) == 1
                }

                # Calculate total shared count
                total_shared = sum(
                    min(current_deck_cards[card], sum(qty for _, qty in decks_list))
                    for card, decks_list in shared_cards_info.items()
                )

                console.print(
                    f"\n  {escape(deck_name)} (sharing from: {escape(', '.join(shared_decks))}) - {total_shared} shared cards total:"
                )

                # Show only cards that are in multiple shared decks
                if common_shared_cards:
                    common_count = sum(current_deck_cards[card] for card in common_shared_cards.keys())
                    console.print(f"    Common across shared decks ({common_count} cards):")
                    for card_name in sorted(common_shared_cards.keys()):
                        quantity_in_current = current_deck_cards[card_name]
                        note = "" if card_name in truly_shared.get(deck_name, set()) else " (available in library)"
                        console.print(f"      - {quantity_in_current} {escape(card_name)}{note}")
                else:
                    console.print("    (no cards common across all shared decks)")

                # Show breakdown for each individual shared deck (exclusive cards only)
                for shared_deck_name in shared_decks:
                    if shared_deck_name in deck_cards:
                        shared_deck_cards = deck_cards[shared_deck_name]

                        # Find cards exclusive to this shared deck
                        exclusive_cards = []
                        for card_name in sorted(current_deck_cards.keys()):
                            if card_name in exclusive_shared_cards and card_name in shared_deck_cards:
                                # Verify it's only in this shared deck
                                if (
                                    len(shared_cards_info[card_name]) == 1
                                    and shared_cards_info[card_name][0][0] == shared_deck_name
                                ):
                                    exclusive_cards.append(card_name)

                        if exclusive_cards:
                            console.print(f"    {escape(shared_deck_name)} ({len(exclusive_cards)} exclusive cards):")
                            for card_name in exclusive_cards:
                                note = (
                                    "" if card_name in truly_shared.get(deck_name, set()) else " (available in library)"
                                )
                                console.print(f"      - {current_deck_cards[card_name]} {escape(card_name)}{note}")
                        else:
                            console.print(f"      {escape(shared_deck_name)} (0 exclusive cards)")
            else:
                # Single shared deck - show all shared cards
                total_shared = sum(
                    min(current_deck_cards[card], sum(qty for _, qty in decks_list))
                    for card, decks_list in shared_cards_info.items()
                )

                console.print(
                    f"\n  {escape(deck_name)} (sharing from: {escape(', '.join(shared_decks))}) - {total_shared} shared cards:"
                )
                for card_name in sorted(shared_cards_info.keys()):
                    quantity_in_current = current_deck_cards[card_name]
                    note = "" if card_name in truly_shared.get(deck_name, set()) else " (available in library)"
                    console.print(f"    - {quantity_in_current} {escape(card_name)}{note}")

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
    console.print(tbl)

    # Build structured deck data for downstream use
    decks = [(name, deck, info) for name, ok, _, deck, info in results if ok]

    owned_cards = _update_owned_cards(binder_id=config["binder_id"])
    _process_purchased_cards(config=config)

    _calculate_available_cards(owned_cards, decks, config)
