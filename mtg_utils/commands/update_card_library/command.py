import os
from collections import Counter

import click
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, TextColumn

from mtg_utils.commands.update_card_library.logic import DeckFetchResult, _compute_card_usage
from mtg_utils.commands.update_card_library.render import (
    render_deck_sync_panel,
    render_failed_deck_warning,
    render_shared_deck_panels,
    render_unavailable_warnings,
)
from mtg_utils.utils.cards import parse_card_list
from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, AppConfig, DeckConfig, load_config
from mtg_utils.utils.console import console
from mtg_utils.utils.moxfield_api import get_deck_list, get_library, library_sort_key
from mtg_utils.utils.readers import read_list


def _update_owned_cards(binder_id) -> list[str]:
    owned_cards = get_library(binder_id=binder_id)
    os.makedirs("card_library", exist_ok=True)
    with open("card_library/owned_cards.txt", "w") as file:
        for card in owned_cards:
            file.write(f"{card}\n")
    console.print("[green]✓[/green] Updated owned cards: card_library/owned_cards.txt")
    return owned_cards


def _process_purchased_cards(config: AppConfig) -> list[str]:
    purchased_file = config.purchased_file

    if not os.path.exists(path=purchased_file):
        console.print(f"[green]✓[/green] Creating empty purchased cards file at {escape(purchased_file)}")
        os.makedirs(os.path.dirname(purchased_file), exist_ok=True)
        with open(purchased_file, "w") as file:
            pass
        return []

    raw_cards = read_list(purchased_file)
    card_counter = Counter(raw_cards)
    purchased_cards = [f"{quantity} {card}" for card, quantity in card_counter.items()]

    purchased_formatted_file = config.purchased_formatted_file
    with open(file=purchased_formatted_file, mode="w") as file:
        for card in sorted(purchased_cards):
            file.write(f"{card}\n")

    console.print(
        f"[green]✓[/green] Processed purchased cards: {len(purchased_cards)} unique cards from {len(raw_cards)} total entries"
    )
    return purchased_cards


def _calculate_available_cards(
    library: list[str], decks: list[tuple[str, list[str], DeckConfig]], config: AppConfig
) -> list[str]:
    """Calculate available cards by subtracting deck cards from the library.

    Supports shared_decks: if a deck has a 'shared_decks' list in its config, it will reuse cards from those
    decks without consuming additional cards from the library pool. Only the remainder is consumed.
    """
    purchased_names: set[str] = set()
    purchased_file = config.purchased_formatted_file
    if purchased_file:
        try:
            purchased_names = set(parse_card_list(read_list(purchased_file)).keys())
        except FileNotFoundError:
            pass

    library_dict = parse_card_list(library)
    deck_cards = {name: parse_card_list(cards) for name, cards, _ in decks}

    used_cards, unavailable_cards, deck_configs = _compute_card_usage(library_dict, deck_cards, decks)

    render_unavailable_warnings(unavailable_cards, purchased_names)
    render_shared_deck_panels(deck_cards, deck_configs)

    available_cards = sorted(
        [
            f"{qty} {name}"
            for name, qty in ((name, library_dict[name] - used_cards.get(name, 0)) for name in library_dict)
            if qty > 0
        ],
        key=library_sort_key,
    )

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

    results: list[DeckFetchResult] = []
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console, transient=True) as progress:
        for deck_name, deck_info in config.decks.items():
            task = progress.add_task(f"Fetching [bold]{escape(deck_name)}[/bold]\u2026", total=None)
            deck = get_deck_list(deck_info.id)
            progress.remove_task(task)
            if deck:
                os.makedirs(os.path.dirname(deck_info.file), exist_ok=True)
                with open(deck_info.file, mode="w") as file:
                    for card in deck:
                        file.write(f"{card}\n")
                results.append(DeckFetchResult(deck_name, True, deck_info.file, deck, deck_info))
            else:
                render_failed_deck_warning(deck_name)
                results.append(DeckFetchResult(deck_name, False, "—", [], deck_info))

    render_deck_sync_panel(results)

    decks = [(r.name, r.cards, r.config) for r in results if r.ok]

    owned_cards = _update_owned_cards(binder_id=config.binder_id)
    _process_purchased_cards(config=config)
    _calculate_available_cards(owned_cards, decks, config)
