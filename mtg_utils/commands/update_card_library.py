import os
from collections import Counter

import click

from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config
from mtg_utils.utils.moxfield_api import get_deck_list, get_library, library_sort_key
from mtg_utils.utils.readers import read_list


def _update_built_decks(config) -> list[tuple[str, list[str], dict]]:
    """Returns list of tuples: (deck_name, card_list, deck_config)"""
    decks = []
    for deck_name, deck_info in config["decks"].items():
        deck = get_deck_list(deck_info["id"])
        if deck:
            decks.append((deck_name, deck, deck_info))

            # Ensure directory exists
            os.makedirs(os.path.dirname(deck_info["file"]), exist_ok=True)

            with open(deck_info["file"], mode="w") as file:
                for card in deck:
                    file.write(f"{card}\n")
            print(f"Updated {deck_name} deck: {deck_info['file']}")
        else:
            print(f"Failed to retrieve {deck_name} deck from Moxfield.")
    return decks


def _update_owned_cards(binder_id) -> list[str]:
    owned_cards = get_library(binder_id=binder_id)

    # Ensure directory exists
    os.makedirs("card_library", exist_ok=True)

    with open("card_library/owned_cards.txt", "w") as file:
        for card in owned_cards:
            file.write(f"{card}\n")
    print("Updated owned cards: card_library/owned_cards.txt")
    return owned_cards


def _process_purchased_cards(config) -> list[str]:
    purchased_file = config.get("purchased_file", "card_library/purchased.txt")

    # Check if purchased.txt exists
    if not os.path.exists(path=purchased_file):
        print(f"Creating empty purchased cards file at {purchased_file}")
        # Ensure directory exists
        os.makedirs(os.path.dirname(purchased_file), exist_ok=True)
        # Create empty file
        with open(purchased_file, "w") as file:
            pass
        return []

    raw_cards = read_list(purchased_file)
    card_counter = Counter(raw_cards)
    purchased_cards = [f"{quantity} {card}" for card, quantity in card_counter.items()]

    with open(file="card_library/purchased_formatted.txt", mode="w") as file:
        for card in sorted(purchased_cards):
            file.write(f"{card}\n")

    print(f"Processed purchased cards: {len(purchased_cards)} unique cards from {len(raw_cards)} total entries")
    return purchased_cards


def _calculate_available_cards(
    library: list[str], decks: list[tuple[str, list[str], dict]], purchased_cards: list[str], config: dict
) -> list[str]:
    """Calculate available cards by subtracting deck cards from the library and adding purchased cards.

    Supports shared_decks: if a deck has a 'shared_decks' list in its config, it will reuse cards from those
    decks without consuming additional cards from the library pool. Only the remainder is consumed.
    """
    # Convert library to dictionary
    library_dict = {}
    for card_entry in library:
        parts = card_entry.split(" ", 1)
        quantity = int(parts[0])
        card_name = parts[1]
        library_dict[card_name] = quantity

    # Add purchased cards to library
    if purchased_cards:
        for card_entry in purchased_cards:
            parts = card_entry.split(" ", 1)
            quantity = int(parts[0])
            card_name = parts[1]

            if card_name in library_dict:
                library_dict[card_name] += quantity
            else:
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

    for deck_name, deck, deck_config in decks:
        deck_configs[deck_name] = deck_config
        deck_unavailable = []
        shared_decks = deck_config.get("shared_decks", [])

        # Validate shared_decks
        for shared_deck_name in shared_decks:
            if shared_deck_name not in deck_cards:
                print(f"WARNING: Deck '{deck_name}' references non-existent shared deck '{shared_deck_name}'")

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

            if available_quantity < quantity_to_consume:
                msg = f"{quantity} {card_name} (have {total_in_library}"
                if shared_details:
                    msg += f", sharing: {', '.join(shared_details)}"
                if already_used > 0 and card_name in card_usage_by_deck:
                    decks_using = ", ".join([f"{q} in {dn}" for dn, q in card_usage_by_deck[card_name].items()])
                    msg += f", already used: {decks_using}"
                msg += ")"
                deck_unavailable.append(msg)

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
        print("\nWARNING: Some cards in decks are not available in the available cards:")
        for deck_name, cards in unavailable_cards.items():
            print(f"\n  {deck_name} deck is missing:")
            for card in cards:
                print(f"    - {card}")

    # Show shared decks information for all decks that have shared_decks configured
    decks_with_sharing = [(name, cfg) for name, cfg in deck_configs.items() if cfg.get("shared_decks")]
    if decks_with_sharing:
        print("\nShared decks configuration:")
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

                print(f"\n  {deck_name} (sharing from: {', '.join(shared_decks)}) - {total_shared} shared cards total:")

                # Show only cards that are in multiple shared decks
                if common_shared_cards:
                    common_count = sum(current_deck_cards[card] for card in common_shared_cards.keys())
                    print(f"    Common across shared decks ({common_count} cards):")
                    for card_name in sorted(common_shared_cards.keys()):
                        quantity_in_current = current_deck_cards[card_name]
                        print(f"      - {quantity_in_current} {card_name}")
                else:
                    print("    (no cards common across all shared decks)")

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
                            print(f"    {shared_deck_name} ({len(exclusive_cards)} exclusive cards):")
                            for card_name in exclusive_cards:
                                print(f"      - {current_deck_cards[card_name]} {card_name}")
                        else:
                            print(f"      {shared_deck_name} (0 exclusive cards)")
            else:
                # Single shared deck - show all shared cards
                total_shared = sum(
                    min(current_deck_cards[card], sum(qty for _, qty in decks_list))
                    for card, decks_list in shared_cards_info.items()
                )

                print(f"\n  {deck_name} (sharing from: {', '.join(shared_decks)}) - {total_shared} shared cards:")
                for card_name in sorted(shared_cards_info.keys()):
                    quantity_in_current = current_deck_cards[card_name]
                    print(f"    - {quantity_in_current} {card_name}")

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
    print("Updated available cards: card_library/available_cards.txt")
    return available_cards


@click.command()
@click.option("--config-file", help="Path to the config file", default=DEFAULT_CONFIG_FILE)
def update_card_library(config_file) -> None:
    """Update the card library with built decks and owned cards."""

    config = load_config(config_file=config_file)
    decks = _update_built_decks(config=config)
    owned_cards = _update_owned_cards(binder_id=config["binder_id"])
    purchased_cards = _process_purchased_cards(config=config)

    _calculate_available_cards(owned_cards, decks, purchased_cards, config)
