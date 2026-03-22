from collections import defaultdict


def compute_missing_cards(
    deck_dict: dict[str, int],
    available_dict: dict[str, int],
    owned_dict: dict[str, int],
    cards_in_decks: dict[str, list[tuple[str, int]]],
) -> tuple[
    list[tuple[str, int]],
    list[tuple[str, int, str]],
    list[str],
    dict[str, list[tuple[str, int, int]]],
]:
    """Compute availability of deck cards against owned/purchased pool.

    Returns:
        completely_missing_cards: [(card_name, missing_qty)]
        partially_missing_cards: [(card_name, qty_from_decks, deck_info_str)]
        available_in_deck: ["qty card_name" strings]
        cards_by_deck: {deck_name: [(card_name, total_qty, usable_qty)]}
    """
    completely_missing_cards: list[tuple[str, int]] = []
    partially_missing_cards: list[tuple[str, int, str]] = []
    available_in_deck: list[str] = []
    cards_by_deck: dict[str, list] = defaultdict(list)

    for card_name, deck_quantity in deck_dict.items():
        available_quantity = available_dict.get(card_name, 0)

        if available_quantity < deck_quantity:
            missing_quantity = deck_quantity - available_quantity
            in_other_decks = cards_in_decks.get(card_name, [])
            total_in_other_decks = sum(qty for _, qty in in_other_decks)

            if total_in_other_decks > 0:
                used_decks = []
                if total_in_other_decks >= missing_quantity:
                    for other_deck, qty in sorted(in_other_decks):
                        cards_by_deck[other_deck].append((card_name, qty, missing_quantity))
                        used_decks.append((other_deck, missing_quantity))
                    deck_info = ", ".join([f"{dn} ({mq})" for dn, mq in used_decks])
                    partially_missing_cards.append((card_name, missing_quantity, deck_info))
                else:
                    for other_deck, qty in sorted(in_other_decks):
                        cards_by_deck[other_deck].append((card_name, qty, qty))
                        used_decks.append((other_deck, qty))
                    deck_info = ", ".join([f"{dn} ({qty})" for dn, qty in used_decks])
                    partially_missing_cards.append((card_name, total_in_other_decks, deck_info))
                    completely_missing_cards.append((card_name, missing_quantity - total_in_other_decks))
            else:
                completely_missing_cards.append((card_name, missing_quantity))

            if available_quantity > 0:
                available_in_deck.append(f"{available_quantity} {card_name}")
        else:
            available_in_deck.append(f"{deck_quantity} {card_name}")

    return completely_missing_cards, partially_missing_cards, available_in_deck, dict(cards_by_deck)
