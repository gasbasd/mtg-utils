import re
from collections import Counter
from decimal import Decimal

MOXFIELD_COLUMNS = [
    "Count",
    "Name",
    "Edition",
    "Condition",
    "Language",
    "Foil",
    "Collector Number",
    "Alter",
    "Playtest Card",
    "Purchase Price",
]

REQUIRED_COLUMNS = [
    "Game",
    "Set Code",
    "Set Name",
    "Item Name",
    "Price in EUR Cents",
    "Quantity",
    "Condition",
    "Language",
    "Foil/Reverse",
    "Collector Number",
]

MAGIC_GAME = "Magic: the Gathering"

# Moxfield's own scale is Mint / Near Mint / Slightly Played / Moderately Played /
# Heavily Played / Damaged, but its importer also accepts the "Lightly Played" wording
# used here. Don't "correct" it: this mapping is the one proven to import cleanly.
CONDITION_MAP = {
    "Mint": "Mint",
    "Near Mint": "Near Mint",
    "Slightly Played": "Lightly Played",
    "Moderately Played": "Moderately Played",
    "Played": "Heavily Played",
    "Heavily Played": "Heavily Played",
    "Poor": "Damaged",
}

# CardTrader uses the code printed on the card; Moxfield uses its own canonical code.
# Codes that agree (en, it, fr, de, pt, ru, es, ph) need no entry, and an unrecognised
# code is passed through untouched rather than failing the whole order.
LANGUAGE_MAP = {
    "jp": "ja",
    "kr": "ko",
    "cn": "zhs",
    "cs": "zhs",
    "tw": "zht",
    "ct": "zht",
    "sp": "es",
}

# CardTrader appends a printing qualifier to the card name: "All That Glitters (Borderless)",
# "Spirit Link (Retro Frame)", "Smashing Spree (856 | Tutorial 18)". Moxfield wants the bare name.
NAME_QUALIFIER = re.compile(r"\s+\([^()]*\)$")

# CardTrader splits a set's collector-booster printings into "<Set> Collectors", coded with a
# leading C (CDFT, CCMM, CDMR). They are the same Scryfall set, with the same collector numbers.
COLLECTORS_SUFFIX = " Collectors"

# CardTrader pages an oversized set by suffixing a digit (PLIST2, LEG2); the base code is the
# one Scryfall knows. Real set codes are never shorter than three characters, which keeps sets
# that simply end in a digit (2X2, MH2, M21) from being trimmed into something else.
TRAILING_DIGITS = re.compile(r"\d+$")
MIN_SET_CODE = 3

# Token collector numbers come in many shapes -- "T 4/2", "F 22/1", "T013", "7/018" -- and the
# printing lives in a T-prefixed set. This pulls out the leading number to retry the lookup with.
TOKEN_COLLECTOR = re.compile(r"^[A-Za-z]?\s*0*(\d+)")


def cell_text(value: str | float | bool) -> str:
    """Render a raw spreadsheet cell as the text a CSV column expects."""
    if isinstance(value, bool):
        return "TRUE" if value else ""
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value).strip()


def identity(name: str, set_code: str, collector_number: str) -> str:
    """How a printing is written in the conversion report: 'Spirit Link | DMR 274'."""
    return f"{name} | {set_code} {collector_number}".rstrip()


def strip_name_qualifier(name: str) -> str:
    """Drop CardTrader's printing qualifier: 'All That Glitters (Borderless)' -> 'All That Glitters'."""
    return NAME_QUALIFIER.sub("", name)


def base_set_code(set_code: str, set_name: str) -> str:
    """Reduce a '<Set> Collectors' pseudo-set to the base set Scryfall and Moxfield know."""
    if set_name.endswith(COLLECTORS_SUFFIX) and len(set_code) > 1 and set_code.startswith("C"):
        return set_code[1:]
    return set_code


def printing_identifier(entry: dict[str, str]) -> dict[str, str]:
    """The Scryfall identifier for a converted row, as CardTrader described it."""
    return {"set": entry["Edition"], "collector_number": entry["Collector Number"]}


def token_identifier(entry: dict[str, str]) -> dict[str, str] | None:
    """The same row retried as a token: a T-prefixed set and the bare leading number."""
    match = TOKEN_COLLECTOR.match(entry["Collector Number"])
    if not match or not entry["Edition"]:
        return None
    return {"set": f"T{entry['Edition']}", "collector_number": match.group(1)}


def set_candidates(entry: dict[str, str]) -> list[str]:
    """Set codes worth searching for this row: what CardTrader said, then its base code."""
    edition = entry["Edition"]
    if not edition:
        return []
    trimmed = TRAILING_DIGITS.sub("", edition)
    if trimmed == edition or len(trimmed) < MIN_SET_CODE:
        return [edition]
    return [edition, trimmed]


def strip_leading_zeros(text: str) -> str:
    """Drop the zero padding CardTrader adds to collector numbers ('035' -> '35')."""
    return re.sub(r"^0+", "", text)


def format_price(cents: str | float | bool) -> str:
    """Convert a price in cents to euros, without trailing zeros (60 -> '0.6')."""
    amount = Decimal(round(float(cell_text(cents) or 0))) / 100
    return format(amount.quantize(Decimal("0.01")), "f").rstrip("0").rstrip(".")


def is_foil(value: str | float | bool) -> bool:
    """Interpret CardTrader's Foil/Reverse flag, whatever cell type it arrives as."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return value.strip().lower() in {"true", "1", "yes", "foil"}


def convert_order_rows(
    rows: list[dict[str, str | float | bool]],
) -> tuple[list[dict[str, str]], list[str], dict[str, dict[str, int]]]:
    """Convert CardTrader order rows into Moxfield collection-importer rows.

    Returns:
        converted: rows keyed by MOXFIELD_COLUMNS, in the order they appeared
        skipped: names of the non-Magic rows that were dropped
        breakdown: {"Condition"|"Language"|"Foil": {value: count}} for the summary
    """
    if not rows:
        raise ValueError("The order file contains no rows.")

    missing = [column for column in REQUIRED_COLUMNS if column not in rows[0]]
    if missing:
        raise ValueError(f"The order file is missing the column(s): {', '.join(missing)}.")

    converted: list[dict[str, str]] = []
    skipped: list[str] = []

    for row in rows:
        name = cell_text(row["Item Name"])
        if cell_text(row["Game"]) != MAGIC_GAME:
            skipped.append(name)
            continue

        condition = cell_text(row["Condition"])
        if condition not in CONDITION_MAP:
            raise ValueError(f"Unknown condition '{condition}' for '{name}'.")

        language = cell_text(row["Language"])
        set_code = cell_text(row["Set Code"])
        collector = strip_leading_zeros(cell_text(row["Collector Number"]))
        converted.append(
            {
                "Count": cell_text(row["Quantity"]),
                "Name": strip_name_qualifier(name),
                "Edition": base_set_code(set_code, cell_text(row["Set Name"])),
                "Condition": CONDITION_MAP[condition],
                "Language": LANGUAGE_MAP.get(language, language),
                "Foil": "foil" if is_foil(row["Foil/Reverse"]) else "",
                "Collector Number": collector,
                "Alter": "",
                "Playtest Card": "",
                "Purchase Price": format_price(row["Price in EUR Cents"]),
                "Source": identity(name, set_code, collector),
            }
        )

    breakdown = {
        "Condition": dict(Counter(entry["Condition"] for entry in converted)),
        "Language": dict(Counter(entry["Language"] for entry in converted)),
        "Foil": dict(Counter("foil" if entry["Foil"] else "non-foil" for entry in converted)),
    }
    return converted, skipped, breakdown


def apply_printings(
    converted: list[dict[str, str]],
    printings: dict[int, dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[str]]:
    """Replace each row's identity with the Scryfall printing resolved for it.

    Rows Scryfall could not confirm keep whatever the conversion rules produced.

    Returns:
        rows: the converted rows, with confirmed names, editions and collector numbers
        corrections: [{"before", "after"}] for every row that changed along the way
        unresolved: identities Scryfall could not confirm, for the reader to check by hand
    """
    rows: list[dict[str, str]] = []
    corrections: list[dict[str, str]] = []
    unresolved: list[str] = []

    for index, entry in enumerate(converted):
        row = dict(entry)
        printing = printings.get(index)
        if printing is not None:
            row["Name"] = printing["name"]
            row["Edition"] = printing["set"]
            row["Collector Number"] = printing["collector_number"]

        after = identity(row["Name"], row["Edition"], row["Collector Number"])
        if printing is None:
            unresolved.append(after)
        elif after != row["Source"]:
            corrections.append({"before": row["Source"], "after": after})

        rows.append(row)

    return rows, corrections, unresolved
