def parse_card_list(entries: list[str]) -> dict[str, int]:
    """Parse '2 Card Name' entries into {card_name: quantity}."""
    result: dict[str, int] = {}
    for entry in entries:
        qty_str, _, name = entry.partition(" ")
        result[name] = int(qty_str)
    return result


def parse_card_list_or_names(entries: list[str]) -> dict[str, int]:
    """Parse entries that may or may not have a quantity prefix.
    Lines like '2 Card Name' → {Card Name: 2}.
    Lines like 'Card Name' (no leading int) → {Card Name: 1}.
    """
    result: dict[str, int] = {}
    for entry in entries:
        qty_str, sep, name = entry.partition(" ")
        if sep and qty_str.isdigit():
            result[name] = int(qty_str)
        else:
            result[entry] = 1
    return result
