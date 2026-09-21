from typing import Literal, NamedTuple

DeckFormat = Literal["commander", "pauper"]

# Cards exempt from the per-copy limit in every format.
BASIC_LANDS: frozenset[str] = frozenset(
    {
        "Plains",
        "Island",
        "Swamp",
        "Mountain",
        "Forest",
        "Wastes",
        "Snow-Covered Plains",
        "Snow-Covered Island",
        "Snow-Covered Swamp",
        "Snow-Covered Mountain",
        "Snow-Covered Forest",
    }
)


class FormatRules(NamedTuple):
    main_size: int
    main_size_exact: bool  # exact size (commander) vs. minimum (60-card constructed)
    sideboard_max: int  # 0 means the format has no sideboard, so none is fetched
    max_copies: int  # basics exempt


FORMATS: dict[str, FormatRules] = {
    "commander": FormatRules(main_size=100, main_size_exact=True, sideboard_max=0, max_copies=1),
    "pauper": FormatRules(main_size=60, main_size_exact=False, sideboard_max=15, max_copies=4),
}


def validate_deck(mainboard: dict[str, int], sideboard: dict[str, int], rules: FormatRules) -> list[str]:
    """Return human-readable rule violations for a deck; empty when it is legal."""
    violations: list[str] = []

    main_total = sum(mainboard.values())
    if rules.main_size_exact and main_total != rules.main_size:
        violations.append(f"{main_total} cards in mainboard (need exactly {rules.main_size})")
    elif not rules.main_size_exact and main_total < rules.main_size:
        violations.append(f"{main_total} cards in mainboard (need at least {rules.main_size})")

    side_total = sum(sideboard.values())
    if side_total > rules.sideboard_max:
        violations.append(f"{side_total} cards in sideboard (max {rules.sideboard_max})")

    copies: dict[str, int] = dict(mainboard)
    for name, qty in sideboard.items():
        copies[name] = copies.get(name, 0) + qty
    for name in sorted(copies):
        if name not in BASIC_LANDS and copies[name] > rules.max_copies:
            violations.append(f"{copies[name]}x {name} (max {rules.max_copies}, counting sideboard)")

    return violations
