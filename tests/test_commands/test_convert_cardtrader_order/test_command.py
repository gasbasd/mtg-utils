import os
from unittest.mock import patch

import pytest
import requests
from click.testing import CliRunner
from xlrd.biffh import XLRDError

from mtg_utils.commands.convert_cardtrader_order.command import convert_cardtrader_order

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "cardtrader_sample.xls")

COMMAND = "mtg_utils.commands.convert_cardtrader_order.command"


def _row(**overrides):
    row = {
        "Game": "Magic: the Gathering",
        "Set Name": "The Hobbit",
        "Set Code": "HOB",
        "Item Name": "Attercop",
        "Price in EUR Cents": 12.0,
        "Quantity": 1.0,
        "Condition": "Near Mint",
        "Language": "en",
        "Foil/Reverse": False,
        "Collector Number": "116",
    }
    row.update(overrides)
    return row


def _touch(tmp_path, name="order.xls"):
    order = tmp_path / name
    order.write_bytes(b"not really a workbook")
    return order


def _scryfall(catalogue=None):
    """Patch the Scryfall client so lookups answer from an in-memory catalogue."""
    known = {key: dict(value) for key, value in (catalogue or {}).items()}

    def find_printings(identifiers):
        found = {}
        for identifier in identifiers:
            key = (identifier["set"].upper(), identifier["collector_number"])
            if key in known:
                found[key] = known[key]
        return found

    return (
        patch(f"{COMMAND}.find_printings", side_effect=find_printings),
        patch(f"{COMMAND}.search_in_set", return_value=None),
        patch(f"{COMMAND}.search_printing", return_value=None),
    )


def _run(order, catalogue=None, rows=None, extra_args=(), **patch_kwargs):
    finder, set_searcher, searcher = _scryfall(catalogue)
    with finder, set_searcher, searcher:
        if rows is None:
            return CliRunner().invoke(convert_cardtrader_order, [str(order), *extra_args])
        with patch(f"{COMMAND}.read_xls_rows", return_value=rows, **patch_kwargs):
            return CliRunner().invoke(convert_cardtrader_order, [str(order), *extra_args])


ATTERCOP = {("HOB", "116"): {"name": "Attercop", "set": "HOB", "collector_number": "116"}}


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_default_output_path_is_derived_from_the_input(tmp_path):
    order = _touch(tmp_path)

    result = _run(order, ATTERCOP, rows=[_row()])

    assert result.exit_code == 0
    assert "Attercop" in (tmp_path / "order-moxfield.csv").read_text()


@pytest.mark.integration
def test_output_file_option_is_honoured(tmp_path):
    order = _touch(tmp_path)
    destination = tmp_path / "elsewhere.csv"

    result = _run(order, ATTERCOP, rows=[_row()], extra_args=["-o", str(destination)])

    assert result.exit_code == 0
    assert destination.exists()
    assert not (tmp_path / "order-moxfield.csv").exists()


@pytest.mark.integration
def test_written_csv_matches_the_moxfield_format(tmp_path):
    order = _touch(tmp_path)
    destination = tmp_path / "out.csv"
    rows = [
        _row(**{"Item Name": "Zada, Hedron Grinder", "Collector Number": "0155", "Foil/Reverse": True}),
        _row(**{"Price in EUR Cents": 60.0}),
    ]
    catalogue = {
        ("HOB", "155"): {"name": "Zada, Hedron Grinder", "set": "HOB", "collector_number": "155"},
        **ATTERCOP,
    }

    result = _run(order, catalogue, rows=rows, extra_args=["-o", str(destination)])

    assert result.exit_code == 0
    raw = destination.read_bytes()
    assert raw.startswith(
        b"Count,Name,Edition,Condition,Language,Foil,Collector Number,Alter,Playtest Card,Purchase Price\r\n"
    )
    assert b'1,"Zada, Hedron Grinder",HOB,Near Mint,en,foil,155,,,0.12\r\n' in raw
    assert b"1,Attercop,HOB,Near Mint,en,,116,,,0.6\r\n" in raw
    assert b"Source" not in raw


# ---------------------------------------------------------------------------
# Scryfall verification
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_collectors_set_is_corrected_and_reported(tmp_path):
    order = _touch(tmp_path)
    destination = tmp_path / "out.csv"
    rows = [
        _row(
            **{
                "Item Name": "Spirit Link (Retro Frame)",
                "Set Name": "Dominaria Remastered Collectors",
                "Set Code": "CDMR",
                "Collector Number": "274",
            }
        )
    ]
    catalogue = {("DMR", "274"): {"name": "Spirit Link", "set": "DMR", "collector_number": "274"}}

    result = _run(order, catalogue, rows=rows, extra_args=["-o", str(destination)])

    assert result.exit_code == 0
    assert "1,Spirit Link,DMR,Near Mint,en,,274,,,0.12" in destination.read_text()
    assert "Corrected: 1" in result.output
    assert "CDMR" in result.output


@pytest.mark.integration
def test_a_token_is_retried_against_its_own_set(tmp_path):
    order = _touch(tmp_path)
    destination = tmp_path / "out.csv"
    rows = [_row(**{"Item Name": "Goblin Army // Human Soldier", "Collector Number": "T 4/2"})]
    catalogue = {("THOB", "4"): {"name": "Goblin Army", "set": "THOB", "collector_number": "4"}}

    result = _run(order, catalogue, rows=rows, extra_args=["-o", str(destination)])

    assert result.exit_code == 0
    assert "1,Goblin Army,THOB,Near Mint,en,,4,,,0.12" in destination.read_text()
    assert "Corrected: 1" in result.output


@pytest.mark.integration
def test_name_search_is_the_last_resort(tmp_path):
    order = _touch(tmp_path)
    destination = tmp_path / "out.csv"
    rows = [_row(**{"Item Name": "Smashing Spree (856 | Tutorial 18)", "Set Code": "MSHB", "Collector Number": "856"})]

    with (
        patch(f"{COMMAND}.read_xls_rows", return_value=rows),
        patch(f"{COMMAND}.find_printings", return_value={}),
        patch(f"{COMMAND}.search_in_set", return_value=None),
        patch(
            f"{COMMAND}.search_printing",
            return_value={"name": "Smashing Spree", "set": "MSC", "collector_number": "856"},
        ) as searcher,
    ):
        result = CliRunner().invoke(convert_cardtrader_order, [str(order), "-o", str(destination)])

    assert result.exit_code == 0
    searcher.assert_called_once_with("Smashing Spree", "856")
    assert "1,Smashing Spree,MSC,Near Mint,en,,856,,,0.12" in destination.read_text()


@pytest.mark.integration
def test_a_set_numbered_its_own_way_is_found_by_name(tmp_path):
    """CardTrader calls The List MB1 and reports only the numeric tail of MIR-89."""
    order = _touch(tmp_path)
    destination = tmp_path / "out.csv"
    rows = [_row(**{"Item Name": "Sapphire Charm", "Set Code": "MB1", "Collector Number": "089"})]

    with (
        patch(f"{COMMAND}.read_xls_rows", return_value=rows),
        patch(f"{COMMAND}.find_printings", return_value={}),
        patch(
            f"{COMMAND}.search_in_set",
            return_value={"name": "Sapphire Charm", "set": "PLST", "collector_number": "MIR-89"},
        ) as set_searcher,
        patch(f"{COMMAND}.search_printing", return_value=None) as searcher,
    ):
        result = CliRunner().invoke(convert_cardtrader_order, [str(order), "-o", str(destination)])

    assert result.exit_code == 0
    set_searcher.assert_called_once_with("Sapphire Charm", "MB1")
    searcher.assert_not_called()
    assert "1,Sapphire Charm,PLST,Near Mint,en,,MIR-89,,,0.12" in destination.read_text()


@pytest.mark.integration
def test_a_paged_set_falls_back_to_its_base_code(tmp_path):
    """CardTrader pages The List as PLIST2 and gives no collector number at all."""
    order = _touch(tmp_path)
    destination = tmp_path / "out.csv"
    rows = [_row(**{"Item Name": "Confound", "Set Code": "PLIST2", "Collector Number": ""})]
    answers = {"PLIST": {"name": "Confound", "set": "PLST", "collector_number": "PLS-22"}}

    with (
        patch(f"{COMMAND}.read_xls_rows", return_value=rows),
        patch(f"{COMMAND}.find_printings", return_value={}),
        patch(f"{COMMAND}.search_in_set", side_effect=lambda name, code: answers.get(code)) as set_searcher,
        patch(f"{COMMAND}.search_printing", return_value=None),
    ):
        result = CliRunner().invoke(convert_cardtrader_order, [str(order), "-o", str(destination)])

    assert result.exit_code == 0
    assert [call.args[1] for call in set_searcher.call_args_list] == ["PLIST2", "PLIST"]
    assert "1,Confound,PLST,Near Mint,en,,PLS-22,,,0.12" in destination.read_text()


@pytest.mark.integration
def test_unresolved_rows_are_reported_but_still_written(tmp_path):
    order = _touch(tmp_path)
    destination = tmp_path / "out.csv"
    rows = [_row(**{"Item Name": "Sapphire Charm", "Set Code": "MB1", "Collector Number": "089"})]

    result = _run(order, {}, rows=rows, extra_args=["-o", str(destination)])

    assert result.exit_code == 0
    assert "check by hand" in result.output
    assert "Sapphire Charm | MB1 89" in result.output
    assert "1,Sapphire Charm,MB1,Near Mint,en,,89,,,0.12" in destination.read_text()


@pytest.mark.integration
def test_scryfall_being_unreachable_still_produces_a_csv(tmp_path):
    order = _touch(tmp_path)
    destination = tmp_path / "out.csv"

    with (
        patch(f"{COMMAND}.find_printings", side_effect=requests.ConnectionError("no route to host")),
        patch(f"{COMMAND}.read_xls_rows", return_value=[_row()]),
    ):
        result = CliRunner().invoke(convert_cardtrader_order, [str(order), "-o", str(destination)])

    assert result.exit_code == 0
    assert "stopped early" in result.output
    assert "1,Attercop,HOB,Near Mint,en,,116,,,0.12" in destination.read_text()


@pytest.mark.integration
def test_a_lookup_failing_partway_keeps_what_was_already_confirmed(tmp_path):
    """A rate limit during the name searches must not discard the batch results."""
    order = _touch(tmp_path)
    destination = tmp_path / "out.csv"
    rows = [_row(), _row(**{"Item Name": "Sapphire Charm", "Set Code": "MB1", "Collector Number": "089"})]

    with (
        patch(f"{COMMAND}.read_xls_rows", return_value=rows),
        patch(f"{COMMAND}.find_printings", side_effect=lambda ids: {("HOB", "116"): ATTERCOP[("HOB", "116")]}),
        patch(f"{COMMAND}.search_in_set", side_effect=requests.HTTPError("429 rate limited")),
    ):
        result = CliRunner().invoke(convert_cardtrader_order, [str(order), "-o", str(destination)])

    assert result.exit_code == 0
    assert "stopped early" in result.output
    contents = destination.read_text()
    assert "1,Attercop,HOB,Near Mint,en,,116,,,0.12" in contents
    assert "1,Sapphire Charm,MB1,Near Mint,en,,89,,,0.12" in contents
    assert "Sapphire Charm | MB1 89" in result.output


# ---------------------------------------------------------------------------
# failure paths
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_missing_order_file(tmp_path):
    result = CliRunner().invoke(convert_cardtrader_order, [str(tmp_path / "nope.xls")])

    assert result.exit_code == 1
    assert "not found" in result.output


@pytest.mark.integration
def test_unreadable_workbook(tmp_path):
    order = _touch(tmp_path)

    with patch(f"{COMMAND}.read_xls_rows", side_effect=XLRDError("Unsupported format")):
        result = CliRunner().invoke(convert_cardtrader_order, [str(order)])

    assert result.exit_code == 1
    assert "Unsupported format" in result.output


@pytest.mark.integration
def test_unknown_condition_aborts(tmp_path):
    order = _touch(tmp_path)

    with patch(f"{COMMAND}.read_xls_rows", return_value=[_row(Condition="Pristine")]):
        result = CliRunner().invoke(convert_cardtrader_order, [str(order)])

    assert result.exit_code == 1
    assert "Attercop" in result.output
    assert not (tmp_path / "order-moxfield.csv").exists()


# ---------------------------------------------------------------------------
# end to end
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_end_to_end_against_a_real_xls(tmp_path):
    """Only Scryfall is stubbed: xlrd, the rules, CSV writing and render all run for real."""
    destination = tmp_path / "out.csv"
    catalogue = {
        ("THOB", "4"): {"name": "Goblin Army", "set": "THOB", "collector_number": "4"},
        ("HOB", "35"): {"name": "Confusticate and Bebother", "set": "HOB", "collector_number": "35"},
        ("MSH", "216"): {
            "name": "Iron Man, Master of Machines",
            "set": "MSH",
            "collector_number": "216",
        },
    }

    result = _run(FIXTURE, catalogue, extra_args=["-o", str(destination)])

    assert result.exit_code == 0
    lines = destination.read_text().splitlines()
    assert lines[0] == (
        "Count,Name,Edition,Condition,Language,Foil,Collector Number,Alter,Playtest Card,Purchase Price"
    )
    assert lines[1:] == [
        "1,Goblin Army,THOB,Near Mint,en,,4,,,0.14",
        "1,Confusticate and Bebother,HOB,Near Mint,en,,35,,,0.13",
        '1,"Iron Man, Master of Machines",MSH,Lightly Played,ja,foil,216,,,0.85',
    ]
    assert "Pikachu" in result.output
    assert "Corrected: 1" in result.output
