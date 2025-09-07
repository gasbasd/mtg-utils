from collections import defaultdict
import os
import click

from mtg_utils.utils.config import DEFAULT_CONFIG_FILE, load_config
from mtg_utils.utils.readers import read_list
from mtg_utils.utils.moxfield_api import get_deck_list

@click.command()
@click.option("--deck-file", "-d", help="Path to the deck file")
@click.option("--moxfield-id", "-id", help="Moxfield ID of the deck to check")
@click.option("--config-file", help="Path to the config file", default=DEFAULT_CONFIG_FILE)
def check_missing_cards(deck_file: str | None, moxfield_id: str | None, config_file: str) -> None:
    """Check for missing cards in a specified deck compared to available cards."""
    if not deck_file and not moxfield_id:
        print("Error: You must provide either --deck-file or --moxfield-id.")
        return
    if deck_file and moxfield_id:
        print("Error: Please provide only one of --deck-file or --moxfield-id.")
        return
    if moxfield_id:
        deck = get_deck_list(moxfield_id)
        if not deck:
            print(f"Error: Could not retrieve deck with Moxfield ID {moxfield_id}.")
            return
    else:
        deck = read_list(deck_file)
    available_cards = read_list("card_library/available_cards.txt")
    config = load_config(config_file)

    # Read all deck files to find cards in other decks
    cards_in_decks = defaultdict(list)
    for deck_name, deck_info in config["decks"].items():
        deck_cards = read_list(deck_info["file"])
        for card_entry in deck_cards:
            parts = card_entry.split(' ', 1)
            quantity = int(parts[0])
            card_name = parts[1]
            cards_in_decks[card_name].append((deck_name, quantity))
    
    # Find missing cards from the deck
    available_dict = {}
    for card_entry in available_cards:
        parts = card_entry.split(' ', 1)
        quantity = int(parts[0])
        card_name = parts[1]
        available_dict[card_name] = quantity
    
    # Find missing and available cards from the deck
    completely_missing_cards = []
    partially_missing_cards = []
    available_in_deck = []
    cards_by_deck = defaultdict(list)
    
    for card_entry in deck:
        parts = card_entry.split(' ', 1)
        deck_quantity = int(parts[0])
        card_name = parts[1]
        
        available_quantity = available_dict.get(card_name, 0)
        
        if available_quantity < deck_quantity:
            missing_quantity = deck_quantity - available_quantity
            
            # Get info about this card in other decks
            in_other_decks = cards_in_decks.get(card_name, [])
            
            # Calculate how many we can get from other decks
            total_available_in_other_decks = sum(min(deck_qty, missing_quantity) for deck_name, deck_qty in in_other_decks)
            
            # Calculate how many are still missing after checking everywhere
            still_missing = missing_quantity - total_available_in_other_decks
            
            # Track cards by deck
            for other_deck, qty in in_other_decks:
                cards_by_deck[other_deck].append((card_name, qty, missing_quantity))
            
            # If we still have missing cards
            if still_missing > 0:
                completely_missing_cards.append((card_name, still_missing))
            
            # If some cards are in other decks
            if total_available_in_other_decks > 0:
                deck_info = ", ".join([f"{deck_name} ({min(qty, missing_quantity)})" for deck_name, qty in in_other_decks])
                partially_missing_cards.append((card_name, total_available_in_other_decks, deck_info))
            
            # If we have some but not enough
            if available_quantity > 0:
                available_in_deck.append(f"{available_quantity} {card_name}")
        else:
            # We have enough of this card
            available_in_deck.append(f"{deck_quantity} {card_name}")
    
    # Display results
    print(f"Total cards in deck: {sum(int(card.split(' ', 1)[0]) for card in deck)}")
            
    # Available cards report
    total_available_qty = sum(int(card.split(' ', 1)[0]) for card in available_in_deck)
    print(f"\nAvailable cards: {total_available_qty} ({len(available_in_deck)} unique)")
    if available_in_deck:
        for card in sorted(available_in_deck):
            print(f"  {card}")
    
    # Completely missing cards report
    total_completely_missing = sum(qty for _, qty in completely_missing_cards)
    if completely_missing_cards:
        print(f"\nMissing cards: {total_completely_missing} ({len(completely_missing_cards)} unique)")
        for card_name, missing_qty in sorted(completely_missing_cards, key=lambda x: x[0]):
            print(f"  {missing_qty} {card_name}")
    else:
        print("All cards can be found in your collection or other decks!")

    # Missing cards in other decks report
    if partially_missing_cards:
        total_in_other_decks = sum(qty for _, qty, _ in partially_missing_cards)
        print(f"\nMissing cards available in other decks ({total_in_other_decks} total, {len(partially_missing_cards)} unique):")
        for card_name, available_qty, deck_info in sorted(partially_missing_cards, key=lambda x: x[0]):
            print(f"  {available_qty} {card_name} - [ {deck_info} ]")

        # Report by deck
        print("\nCards needed from each deck:")
        for deck_name, cards in sorted(cards_by_deck.items()):
            # Calculate total cards available to take from this deck
            total_available_in_deck = sum(min(qty_in_deck, missing_qty) for card_name, qty_in_deck, missing_qty in cards)
            print(f"\n{deck_name} deck ({total_available_in_deck} cards available):")
            for card_name, qty_in_deck, missing_qty in sorted(cards, key=lambda x: x[0]):
                # Only show the quantity we can actually get from this deck
                available_qty = min(qty_in_deck, missing_qty)
                print(f"  {available_qty} {card_name}")
