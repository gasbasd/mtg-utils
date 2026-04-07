import os
from collections import defaultdict

import click
from rich.markup import escape

from mtg_utils.commands.show_shopping_list.logic import compute_shopping_list
from mtg_utils.commands.show_shopping_list.render import render_shopping_list
from mtg_utils.utils.cards import parse_card_list, parse_card_list_or_names
from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config
from mtg_utils.utils.console import err_console
from mtg_utils.utils.moxfield_api import get_deck_list
from mtg_utils.utils.readers import read_list


@click.command()
@click.option("--deck-file", "-d", multiple=True, help="Path to a deck file (repeatable)")
@click.option("--moxfield-id", "-id", multiple=True, help="Moxfield deck ID (repeatable)")
@click.option("--output-file", "-o", default=None, help="Write shopping list to this file")
@click.option("--config-file", default=DEFAULT_CONFIG_FILE, help="Path to config file")
def show_shopping_list(
    deck_file: tuple[str, ...],
    moxfield_id: tuple[str, ...],
    output_file: str | None,
    config_file: str,
) -> None:
    """Generate a consolidated shopping list across multiple decks."""
    if not deck_file and not moxfield_id:
        err_console.print("[red]Error: You must provide at least one --deck-file or --moxfield-id.[/red]")
        raise SystemExit(1)

    try:
        owned_cards = read_list("card_library/available_cards.txt")
    except FileNotFoundError:
        err_console.print(
            "[red]Error: card_library/available_cards.txt not found. Run [bold]update-library[/bold] first.[/red]"
        )
        raise SystemExit(1)

    config = load_config(config_file)
    purchased_quantities: dict[str, int] = {}
    if config.purchased_formatted_file:
        try:
            purchased_quantities = parse_card_list(read_list(config.purchased_formatted_file))
        except FileNotFoundError:
            pass

    # Load raw owned library to compute deck deficit for purchased cards
    try:
        owned_dict_full = parse_card_list(read_list("card_library/owned_cards.txt"))
    except FileNotFoundError:
        owned_dict_full = {}

    available_dict = parse_card_list(owned_cards)

    # Build cards_in_decks and total deck demand per card
    cards_in_decks: dict[str, list[str]] = defaultdict(list)
    total_deck_demand: dict[str, int] = {}
    for deck_name, deck_info in config.decks.items():
        try:
            for card_name, qty in parse_card_list(read_list(deck_info.file)).items():
                cards_in_decks[card_name].append(deck_name)
                total_deck_demand[card_name] = total_deck_demand.get(card_name, 0) + qty
        except FileNotFoundError:
            pass

    # Add only the portion of purchased cards not already spoken for by configured decks
    for card_name, purchased_qty in purchased_quantities.items():
        deck_deficit = max(0, total_deck_demand.get(card_name, 0) - owned_dict_full.get(card_name, 0))
        effective_qty = max(0, purchased_qty - deck_deficit)
        if effective_qty > 0:
            available_dict[card_name] = available_dict.get(card_name, 0) + effective_qty
    purchased_names: set[str] = set(purchased_quantities.keys())

    sources: list[tuple[str, dict[str, int]]] = []
    seen_paths: set[str] = set()

    for path in deck_file:
        abs_path = os.path.abspath(path)
        if abs_path in seen_paths:
            err_console.print(f"[yellow]Warning: Duplicate deck file skipped: {escape(path)}[/yellow]")
            continue
        seen_paths.add(abs_path)
        if not os.path.exists(path):
            err_console.print(f"[yellow]Warning: Deck file not found, skipping: {escape(path)}[/yellow]")
            continue
        label = os.path.basename(path)
        sources.append((label, parse_card_list_or_names(read_list(path))))

    for mid in moxfield_id:
        deck = get_deck_list(mid)
        if not deck:
            err_console.print(f"[yellow]Warning: Could not retrieve Moxfield deck {escape(mid)}, skipping.[/yellow]")
            continue
        sources.append((mid, parse_card_list_or_names(deck)))

    if not sources:
        err_console.print("[red]Error: No valid deck sources could be loaded.[/red]")
        raise SystemExit(1)

    to_buy, already_available = compute_shopping_list(sources, available_dict, dict(cards_in_decks))

    render_shopping_list(to_buy, already_available, len(sources), purchased_names)

    if output_file:
        with open(output_file, "w") as f:
            for card_name, qty, _, __ in to_buy:
                f.write(f"{qty} {card_name}\n")
