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
                # Draw the shortfall down deck by deck: each one lends at most what it holds,
                # and no more than what is still missing.
                used_decks = []
                remaining = missing_quantity
                for other_deck, qty in sorted(in_other_decks):
                    if remaining <= 0:
                        break
                    borrowed = min(qty, remaining)
                    cards_by_deck[other_deck].append((card_name, qty, borrowed))
                    used_decks.append((other_deck, borrowed))
                    remaining -= borrowed
                deck_info = ", ".join([f"{dn} ({bq})" for dn, bq in used_decks])
                partially_missing_cards.append((card_name, missing_quantity - remaining, deck_info))
                if remaining > 0:
                    completely_missing_cards.append((card_name, remaining))
            else:
                completely_missing_cards.append((card_name, missing_quantity))

            if available_quantity > 0:
                available_in_deck.append(f"{available_quantity} {card_name}")
        else:
            available_in_deck.append(f"{deck_quantity} {card_name}")

    return completely_missing_cards, partially_missing_cards, available_in_deck, dict(cards_by_deck)


def board_tags(mainboard: dict[str, int], sideboard: dict[str, int]) -> dict[str, str]:
    """Label cards that live (at least partly) in the sideboard.

    Returns {card_name: "side" | "main+side"}; mainboard-only cards get no entry.
    """
    return {name: "main+side" if name in mainboard else "side" for name in sideboard}
