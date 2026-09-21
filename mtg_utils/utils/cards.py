SIDEBOARD_MARKER = "# Sideboard"


def _is_comment(entry: str) -> bool:
    return entry.startswith("#")


def parse_card_list(entries: list[str]) -> dict[str, int]:
    """Parse '2 Card Name' entries into {card_name: quantity}.

    Repeated entries for one card accumulate, so a list may spread copies over several lines.
    Lines starting with '#' (such as the sideboard marker) are skipped, so a sectioned deck file
    parses as one flat pool.
    """
    result: dict[str, int] = {}
    for entry in entries:
        if _is_comment(entry):
            continue
        qty_str, _, name = entry.partition(" ")
        result[name] = result.get(name, 0) + int(qty_str)
    return result


def parse_card_list_or_names(entries: list[str]) -> dict[str, int]:
    """Parse entries that may or may not have a quantity prefix.
    Lines like '2 Card Name' → {Card Name: 2}.
    Lines like 'Card Name' (no leading int) → {Card Name: 1}.
    Repeated entries for one card accumulate, so four bare lines are four copies.
    Lines starting with '#' are skipped.
    """
    result: dict[str, int] = {}
    for entry in entries:
        if _is_comment(entry):
            continue
        qty_str, sep, name = entry.partition(" ")
        if sep and qty_str.isdigit():
            result[name] = result.get(name, 0) + int(qty_str)
        else:
            result[entry] = result.get(entry, 0) + 1
    return result


def split_boards(entries: list[str]) -> tuple[list[str], list[str]]:
    """Split raw deck lines at the sideboard marker into (mainboard, sideboard).

    Without a marker everything is mainboard.
    """
    for index, entry in enumerate(entries):
        if entry.lower() == SIDEBOARD_MARKER.lower():
            return entries[:index], entries[index + 1 :]
    return list(entries), []
