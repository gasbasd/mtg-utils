from collections import defaultdict

import click
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config
from mtg_utils.utils.console import console, err_console
from mtg_utils.utils.moxfield_api import get_deck_list
from mtg_utils.utils.readers import read_list


@click.command()
@click.option("--deck-file", "-d", help="Path to the deck file")
@click.option("--moxfield-id", "-id", help="Moxfield ID of the deck to check")
@click.option("--config-file", help="Path to the config file", default=DEFAULT_CONFIG_FILE)
def check_missing_cards(deck_file: str | None, moxfield_id: str | None, config_file: str) -> None:
    """Check for missing cards in a specified deck compared to available cards."""
    if not deck_file and not moxfield_id:
        err_console.print("[red]Error: You must provide either --deck-file or --moxfield-id.[/red]")
        raise SystemExit(1)
    if deck_file and moxfield_id:
        err_console.print("[red]Error: Please provide only one of --deck-file or --moxfield-id.[/red]")
        raise SystemExit(1)
    if moxfield_id:
        deck = get_deck_list(moxfield_id)
        if not deck:
            err_console.print(f"[red]Error: Could not retrieve deck with Moxfield ID {escape(moxfield_id)}.[/red]")
            raise SystemExit(1)
    else:
        deck = read_list(deck_file)
    available_cards = read_list("card_library/available_cards.txt")
    config = load_config(config_file)

    # Read all deck files to find cards in other decks
    cards_in_decks = defaultdict(list)
    for deck_name, deck_info in config["decks"].items():
        deck_cards = read_list(deck_info["file"])
        for card_entry in deck_cards:
            parts = card_entry.split(" ", 1)
            quantity = int(parts[0])
            card_name = parts[1]
            cards_in_decks[card_name].append((deck_name, quantity))

    # Load purchased card quantities (for * marker and availability)
    purchased_quantities: dict[str, int] = {}
    purchased_file = config.get("purchased_formatted_file", "")
    if purchased_file:
        try:
            for entry in read_list(purchased_file):
                qty, name = entry.split(" ", 1)
                purchased_quantities[name] = int(qty)
        except FileNotFoundError:
            pass
    purchased_names = set(purchased_quantities.keys())

    # Find missing cards from the deck
    owned_dict: dict[str, int] = {}
    for card_entry in available_cards:
        parts = card_entry.split(" ", 1)
        quantity = int(parts[0])
        card_name = parts[1]
        owned_dict[card_name] = quantity

    # Supplement with purchased quantities (owned_dict stays as-is for marker logic)
    available_dict = dict(owned_dict)
    for card_name, qty in purchased_quantities.items():
        available_dict[card_name] = available_dict.get(card_name, 0) + qty

    # Find missing and available cards from the deck
    completely_missing_cards = []
    partially_missing_cards = []
    available_in_deck = []
    cards_by_deck = defaultdict(list)

    for card_entry in deck:
        parts = card_entry.split(" ", 1)
        deck_quantity = int(parts[0])
        card_name = parts[1]

        available_quantity = available_dict.get(card_name, 0)

        if available_quantity < deck_quantity:
            missing_quantity = deck_quantity - available_quantity

            # Get info about this card in other decks
            in_other_decks = cards_in_decks.get(card_name, [])

            # First count how many decks have this card and total quantity
            total_in_other_decks = sum(qty for _, qty in in_other_decks)

            if total_in_other_decks > 0:
                # Track which decks have this card
                used_decks = []

                # If we can get all we need from other decks
                if total_in_other_decks >= missing_quantity:
                    # Show the same missing_quantity for all decks
                    for other_deck, qty in sorted(in_other_decks):
                        # All decks show the same missing quantity
                        cards_by_deck[other_deck].append((card_name, qty, missing_quantity))
                        used_decks.append((other_deck, missing_quantity))

                    # Record that we found the card in other decks
                    deck_info = ", ".join([f"{deck_name} ({missing_quantity})" for deck_name, _ in used_decks])
                    partially_missing_cards.append((card_name, missing_quantity, deck_info))
                else:
                    # We can't get all we need, so record what we can get
                    for other_deck, qty in sorted(in_other_decks):
                        cards_by_deck[other_deck].append((card_name, qty, qty))
                        used_decks.append((other_deck, qty))

                    # Record partial find and that some are still missing
                    deck_info = ", ".join([f"{deck_name} ({qty})" for deck_name, qty in used_decks])
                    partially_missing_cards.append((card_name, total_in_other_decks, deck_info))
                    completely_missing_cards.append((card_name, missing_quantity - total_in_other_decks))
            else:
                # No copies in other decks
                completely_missing_cards.append((card_name, missing_quantity))

            # If we have some but not enough
            if available_quantity > 0:
                available_in_deck.append(f"{available_quantity} {card_name}")
        else:
            # We have enough of this card
            available_in_deck.append(f"{deck_quantity} {card_name}")

    # Display results
    total = sum(int(card.split(" ", 1)[0]) for card in deck)
    console.print(Rule(f"[bold]Total cards in deck: {total}[/bold]"))

    # Equal panel height: max content rows + 2 border lines
    panel_height = max(len(available_in_deck), len(completely_missing_cards) if completely_missing_cards else 1) + 2

    # Build available panel
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
            height=panel_height,
        )
    else:
        avail_panel = None

    # Build missing panel
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
            height=panel_height,
        )
    else:
        missing_panel = Panel("[green]✓ All cards available![/green]", border_style="green", height=panel_height)

    # Render available + missing side by side with equal size
    if avail_panel:
        grid = Table.grid(expand=True)
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)
        grid.add_row(avail_panel, missing_panel)
        console.print(grid)
    else:
        console.print(missing_panel)

    # Cards in other decks panel
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

        # Per-deck breakdown panels — up to 3 per row
        deck_items = sorted(cards_by_deck.items())
        for i in range(0, len(deck_items), 3):
            row_decks = deck_items[i : i + 3]
            row_height = max(sum(1 for _, _, usable_qty in cards if usable_qty > 0) for _, cards in row_decks) + 2
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
                        height=row_height,
                    )
                )
            grid = Table.grid(expand=True)
            for _ in row_panels:
                grid.add_column(ratio=1)
            grid.add_row(*row_panels)
            console.print(grid)
