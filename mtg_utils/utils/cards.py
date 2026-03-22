def parse_card_list(entries: list[str]) -> dict[str, int]:
    """Parse '2 Card Name' entries into {card_name: quantity}."""
    result: dict[str, int] = {}
    for entry in entries:
        qty_str, _, name = entry.partition(" ")
        result[name] = int(qty_str)
    return result
