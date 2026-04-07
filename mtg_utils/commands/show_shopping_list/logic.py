def compute_shopping_list(
    sources: list[tuple[str, dict[str, int]]],
    available_dict: dict[str, int],
    cards_in_decks: dict[str, list[str]],
) -> tuple[
    list[tuple[str, int, list[str], list[str]]],
    list[tuple[str, int]],  # (card_name, demanded_qty)
]:
    """Compute cards to buy and cards already available across all sources.

    Returns:
        to_buy: [(card_name, qty_to_buy, [source_labels], [config_deck_names])] sorted alphabetically
        already_available: [(card_name, total_demand)] sorted alphabetically by card name
    """
    demand: dict[str, dict[str, int]] = {}
    for label, demand_dict in sources:
        for card_name, qty in demand_dict.items():
            if card_name not in demand:
                demand[card_name] = {}
            demand[card_name][label] = demand[card_name].get(label, 0) + qty

    to_buy: list[tuple[str, int, list[str], list[str]]] = []
    already_available: list[tuple[str, int]] = []

    for card_name, source_map in sorted(demand.items()):
        total_demand = sum(source_map.values())
        qty_to_buy = max(0, total_demand - available_dict.get(card_name, 0))
        if qty_to_buy > 0:
            to_buy.append((card_name, qty_to_buy, sorted(source_map.keys()), sorted(cards_in_decks.get(card_name, []))))
        else:
            already_available.append((card_name, total_demand))

    return to_buy, sorted(already_available, key=lambda x: x[0])
