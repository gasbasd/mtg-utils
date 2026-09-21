import pytest

from mtg_utils.commands.convert_cardtrader_order.render import render_conversion

CONVERTED = [
    {
        "Count": "1",
        "Name": "Attercop",
        "Edition": "HOB",
        "Condition": "Near Mint",
        "Language": "en",
        "Foil": "",
        "Collector Number": "116",
        "Alter": "",
        "Playtest Card": "",
        "Purchase Price": "0.12",
        "Source": "Attercop | HOB 116",
    },
    {
        "Count": "1",
        "Name": "Iron Man, Master of Machines",
        "Edition": "MSH",
        "Condition": "Lightly Played",
        "Language": "ja",
        "Foil": "foil",
        "Collector Number": "216",
        "Alter": "",
        "Playtest Card": "",
        "Purchase Price": "0.85",
        "Source": "Iron Man, Master of Machines | MSH 216",
    },
]

BREAKDOWN = {
    "Condition": {"Near Mint": 1, "Lightly Played": 1},
    "Language": {"en": 1, "ja": 1},
    "Foil": {"non-foil": 1, "foil": 1},
}

CORRECTIONS = [{"before": "Spirit Link (Retro Frame) | CDMR 274", "after": "Spirit Link | DMR 274"}]


@pytest.mark.unit
def test_summary_only(capsys):
    render_conversion(CONVERTED, [], [], [], BREAKDOWN, "orders/out.csv")

    out = capsys.readouterr().out
    assert "0.97" in out
    assert "Near Mint 1" in out
    assert "ja 1" in out
    assert "orders/out.csv" in out
    assert "Skipped" not in out
    assert "Corrected" not in out


@pytest.mark.unit
def test_skipped_rows_are_listed(capsys):
    render_conversion(CONVERTED, ["Pikachu"], [], [], BREAKDOWN, "orders/out.csv")

    out = capsys.readouterr().out
    assert "Pikachu" in out
    assert "Skipped" in out


@pytest.mark.unit
def test_corrections_are_reported(capsys):
    render_conversion(CONVERTED, [], CORRECTIONS, [], BREAKDOWN, "out.csv")

    out = capsys.readouterr().out
    assert "Corrected: 1" in out
    assert "CDMR" in out
    assert "DMR 274" in out


@pytest.mark.unit
def test_unresolved_rows_are_reported(capsys):
    render_conversion(CONVERTED, [], [], ["Sapphire Charm | MB1 89"], BREAKDOWN, "out.csv")

    out = capsys.readouterr().out
    assert "check by hand" in out
    assert "Sapphire Charm" in out


@pytest.mark.unit
def test_notice_is_shown(capsys):
    render_conversion(CONVERTED, [], [], [], BREAKDOWN, "out.csv", "Scryfall was unreachable")

    assert "Scryfall was unreachable" in capsys.readouterr().out


@pytest.mark.unit
def test_empty_conversion(capsys):
    render_conversion([], ["Pikachu"], [], [], {"Condition": {}, "Language": {}, "Foil": {}}, "out.csv")

    out = capsys.readouterr().out
    assert "0.00" in out
    assert "Pikachu" in out
