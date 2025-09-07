import os
import click
from collections import Counter

from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config
from mtg_utils.utils.readers import read_list
from mtg_utils.utils.moxfield_api import get_deck_list, get_library, library_sort_key


def _update_built_decks(config) -> list[tuple[str, list[str]]]:
    decks = []
    for deck_name, deck_info in config["decks"].items():
        deck = get_deck_list(deck_info["id"])
        if deck:
            decks.append((deck_name, deck))
            
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
    print(f"Updated owned cards: card_library/owned_cards.txt")
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

def _calculate_available_cards(library: list[str], 
                               decks: list[tuple[str, list[str]]], 
                               purchased_cards: list[str]) -> list[str]:
    """Calculate available cards by subtracting deck cards from the library and adding purchased cards."""
    # Convert library to dictionary
    library_dict = {}
    for card_entry in library:
        parts = card_entry.split(' ', 1)
        quantity = int(parts[0])
        card_name = parts[1]
        library_dict[card_name] = quantity
    
    # Add purchased cards to library
    if purchased_cards:
        for card_entry in purchased_cards:
            parts = card_entry.split(' ', 1)
            quantity = int(parts[0])
            card_name = parts[1]
            
            if card_name in library_dict:
                library_dict[card_name] += quantity
            else:
                library_dict[card_name] = quantity
    
    # Calculate used cards across decks and check for unavailable cards
    used_cards = {}
    unavailable_cards = {}
    
    for deck_name, deck in decks:
        deck_unavailable = []
        
        for card_entry in deck:
            parts = card_entry.split(' ', 1)
            quantity = int(parts[0])
            card_name = parts[1]
            
            # Track used cards
            if card_name in used_cards:
                used_cards[card_name] += quantity
            else:
                used_cards[card_name] = quantity
            
            # Check if card is available in library
            available_quantity = library_dict.get(card_name, 0)
            if available_quantity < quantity:
                deck_unavailable.append(f"{quantity} {card_name} (have {available_quantity})")
        
        if deck_unavailable:
            unavailable_cards[deck_name] = deck_unavailable
    
    # Print warnings for unavailable cards
    if unavailable_cards:
        print("\nWARNING: Some cards in decks are not available in the available cards:")
        for deck_name, cards in unavailable_cards.items():
            print(f"\n  {deck_name} deck is missing:")
            for card in cards:
                print(f"    - {card}")
    
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
    print(f"Updated available cards: card_library/available_cards.txt")
    return available_cards

@click.command()
@click.option("--config-file", help="Path to the config file", default=DEFAULT_CONFIG_FILE)
def update_card_library(config_file) -> None:
    """Update the card library with built decks and owned cards."""

    config = load_config(config_file=config_file)
    decks = _update_built_decks(config=config)
    owned_cards = _update_owned_cards(binder_id=config["binder_id"])
    purchased_cards = _process_purchased_cards(config=config)

    available_cards = _calculate_available_cards(owned_cards, decks, purchased_cards)
