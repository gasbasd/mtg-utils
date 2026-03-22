from collections import defaultdict

import click
from rich.markup import escape

from mtg_utils.commands.check_missing_cards.logic import compute_missing_cards
from mtg_utils.commands.check_missing_cards.render import render_results
from mtg_utils.utils.cards import parse_card_list
from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config
from mtg_utils.utils.console import err_console
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

    cards_in_decks: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for deck_name, deck_info in config.decks.items():
        for card_name, quantity in parse_card_list(read_list(deck_info.file)).items():
            cards_in_decks[card_name].append((deck_name, quantity))

    purchased_file = config.purchased_formatted_file
    purchased_quantities: dict[str, int] = {}
    if purchased_file:
        try:
            purchased_quantities = parse_card_list(read_list(purchased_file))
        except FileNotFoundError:
            pass
    purchased_names = set(purchased_quantities.keys())

    owned_dict = parse_card_list(available_cards)
    available_dict = dict(owned_dict)
    for card_name, qty in purchased_quantities.items():
        available_dict[card_name] = available_dict.get(card_name, 0) + qty

    deck_dict = parse_card_list(deck)
    total = sum(deck_dict.values())

    completely_missing_cards, partially_missing_cards, available_in_deck, cards_by_deck = compute_missing_cards(
        deck_dict, available_dict, owned_dict, dict(cards_in_decks)
    )

    render_results(
        available_in_deck,
        completely_missing_cards,
        partially_missing_cards,
        cards_by_deck,
        purchased_names,
        owned_dict,
        total,
    )
