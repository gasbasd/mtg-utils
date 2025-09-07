import click

from mtg_utils.utils.readers import read_list



@click.command()
@click.option("--deck1-file", "-d1", help="Path to the deck 1 file")
@click.option("--deck2-file", "-d2", help="Path to the deck 2 file")
def compare_decks(
    deck1_file: str,
    deck2_file: str 
) -> None:
    """Compare two specified decks."""
    deck1 = {}
    for card in read_list(deck1_file):
        parts = card.split(' ', 1)
        if len(parts) == 2:
            quantity, name = parts
            deck1[name] = int(quantity)
    
    deck2 = {}
    for card in read_list(deck2_file):
        parts = card.split(' ', 1)
        if len(parts) == 2:
            quantity, name = parts
            deck2[name] = int(quantity)
    
    # All card names across both decks
    all_cards = set(deck1.keys()) | set(deck2.keys())
    
    # Categorize cards
    common_cards = []
    unique_to_deck1 = []
    unique_to_deck2 = []
    
    for card in all_cards:
        qty1 = deck1.get(card, 0)
        qty2 = deck2.get(card, 0)
        
        if qty1 > 0 and qty2 > 0:
            # Card is in both decks
            common_qty = min(qty1, qty2)
            common_cards.append((card, common_qty))
            
            # Add any excess to unique lists
            if qty1 > common_qty:
                unique_to_deck1.append((card, qty1 - common_qty))
            if qty2 > common_qty:
                unique_to_deck2.append((card, qty2 - common_qty))
        elif qty1 > 0:
            unique_to_deck1.append((card, qty1))
        else:
            unique_to_deck2.append((card, qty2))
    
    # Calculate total quantities
    total_common_qty = sum(qty for _, qty in common_cards)
    total_unique_to_deck1_qty = sum(qty for _, qty in unique_to_deck1)
    total_unique_to_deck2_qty = sum(qty for _, qty in unique_to_deck2)
    
    # Print results
    print(f"Cards in common: {total_common_qty} ({len(common_cards)} unique)\n")
    for card, qty in sorted(common_cards, key=lambda x: x[0]):
        print(f"{qty} {card}")
    
    print(f"\nCards only in {deck1_file}: {total_unique_to_deck1_qty} ({len(unique_to_deck1)} unique)\n")
    for card, qty in sorted(unique_to_deck1, key=lambda x: x[0]):
        print(f"{qty} {card}")
    
    print(f"\nCards only in {deck2_file}: {total_unique_to_deck2_qty} ({len(unique_to_deck2)} unique)\n")
    for card, qty in sorted(unique_to_deck2, key=lambda x: x[0]):
        print(f"{qty} {card}")
