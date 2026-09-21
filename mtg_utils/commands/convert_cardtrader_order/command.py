import csv
import os

import click
import requests
from rich.markup import escape
from xlrd.biffh import XLRDError

from mtg_utils.commands.convert_cardtrader_order.logic import (
    MOXFIELD_COLUMNS,
    apply_printings,
    convert_order_rows,
    printing_identifier,
    set_candidates,
    token_identifier,
)
from mtg_utils.commands.convert_cardtrader_order.render import render_conversion
from mtg_utils.utils.console import err_console
from mtg_utils.utils.readers import read_xls_rows
from mtg_utils.utils.scryfall_api import find_printings, search_in_set, search_printing


def _resolve_batch(
    candidates: dict[int, dict[str, str]],
    resolved: dict[int, dict[str, str]],
) -> None:
    """Look the candidate identifiers up in one go, recording whatever Scryfall confirms."""
    unique = {(identifier["set"].upper(), identifier["collector_number"]): identifier for identifier in candidates.values()}
    found = find_printings(list(unique.values()))
    for index, identifier in candidates.items():
        printing = found.get((identifier["set"].upper(), identifier["collector_number"]))
        if printing is not None:
            resolved[index] = printing


def _resolve_printings(converted: list[dict[str, str]], resolved: dict[int, dict[str, str]]) -> None:
    """Match every converted row to a real Scryfall printing, cheapest lookup first.

    CardTrader invents set codes, so a row that misses on its own identifier is retried as a
    token, then by name within its set, then by name alone. Rows that survive every attempt
    are left for the reader to check.

    Matches are recorded in `resolved` as they are found, so a lookup that fails partway
    through keeps whatever was already confirmed.
    """
    _resolve_batch({index: printing_identifier(entry) for index, entry in enumerate(converted)}, resolved)

    tokens: dict[int, dict[str, str]] = {}
    for index, entry in enumerate(converted):
        identifier = token_identifier(entry)
        if index not in resolved and identifier is not None:
            tokens[index] = identifier
    _resolve_batch(tokens, resolved)

    for index, entry in enumerate(converted):
        if index in resolved:
            continue
        for set_code in set_candidates(entry):
            printing = search_in_set(entry["Name"], set_code)
            if printing is not None:
                resolved[index] = printing
                break

    for index, entry in enumerate(converted):
        if index not in resolved:
            printing = search_printing(entry["Name"], entry["Collector Number"])
            if printing is not None:
                resolved[index] = printing


@click.command()
@click.argument("order_file")
@click.option(
    "--output-file",
    "-o",
    default=None,
    help="Write the Moxfield CSV here (default: <order file>-moxfield.csv)",
)
def convert_cardtrader_order(order_file: str, output_file: str | None) -> None:
    """Convert a CardTrader order .xls into a Moxfield collection import CSV."""
    if not os.path.exists(order_file):
        err_console.print(f"[red]Error: Order file not found: {escape(order_file)}[/red]")
        raise SystemExit(1)

    try:
        rows = read_xls_rows(order_file)
    except XLRDError as error:
        err_console.print(f"[red]Error: Could not read {escape(order_file)} as a .xls file: {escape(str(error))}[/red]")
        raise SystemExit(1)

    try:
        converted, skipped, breakdown = convert_order_rows(rows)
    except ValueError as error:
        err_console.print(f"[red]Error: {escape(str(error))}[/red]")
        raise SystemExit(1)

    notice = None
    printings: dict[int, dict[str, str]] = {}
    try:
        _resolve_printings(converted, printings)
    except requests.RequestException as error:
        notice = f"Scryfall lookups stopped early ({error}); some printings are unverified."

    converted, corrections, unresolved = apply_printings(converted, printings)

    destination = output_file or f"{os.path.splitext(order_file)[0]}-moxfield.csv"
    with open(destination, "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MOXFIELD_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(converted)

    render_conversion(converted, skipped, corrections, unresolved, breakdown, destination, notice)
