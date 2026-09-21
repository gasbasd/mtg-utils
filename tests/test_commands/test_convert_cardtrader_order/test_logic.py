import pytest

from mtg_utils.commands.convert_cardtrader_order.logic import (
    MOXFIELD_COLUMNS,
    apply_printings,
    base_set_code,
    cell_text,
    convert_order_rows,
    format_price,
    identity,
    is_foil,
    printing_identifier,
    set_candidates,
    strip_leading_zeros,
    strip_name_qualifier,
    token_identifier,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _row(**overrides):
    """A CardTrader order row with the cell types xlrd actually produces."""
    row = {
        "Game": "Magic: the Gathering",
        "Set Released At": "2026-08-14",
        "Set Name": "The Hobbit",
        "Set Code": "HOB",
        "Item Name": "Attercop",
        "Price in EUR Cents": 12.0,
        "Quantity": 1.0,
        "Condition": "Near Mint",
        "Language": "en",
        "Foil/Reverse": False,
        "Signed": False,
        "Altered": False,
        "First Edition": "",
        "Collector Number": "116",
    }
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# cell_text
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCellText:
    def test_true_boolean(self):
        assert cell_text(True) == "TRUE"

    def test_false_boolean(self):
        assert cell_text(False) == ""

    def test_whole_float_loses_the_decimal(self):
        assert cell_text(14.0) == "14"

    def test_fractional_float_is_kept(self):
        assert cell_text(2.5) == "2.5"

    def test_text_is_stripped(self):
        assert cell_text("  035  ") == "035"


# ---------------------------------------------------------------------------
# strip_leading_zeros
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStripLeadingZeros:
    def test_padded_number(self):
        assert strip_leading_zeros("035") == "35"

    def test_lone_zero_becomes_empty(self):
        assert strip_leading_zeros("0") == ""

    def test_empty_stays_empty(self):
        assert strip_leading_zeros("") == ""

    def test_token_prefix_is_untouched(self):
        assert strip_leading_zeros("T 4/2") == "T 4/2"

    def test_only_leading_zeros_are_stripped(self):
        assert strip_leading_zeros("7/018") == "7/018"


# ---------------------------------------------------------------------------
# format_price
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatPrice:
    def test_trailing_zero_is_trimmed(self):
        assert format_price(60.0) == "0.6"

    def test_two_decimals(self):
        assert format_price(14.0) == "0.14"

    def test_over_one_euro(self):
        assert format_price(1015.0) == "10.15"

    def test_whole_euro_has_no_decimals(self):
        assert format_price(100.0) == "1"

    def test_zero(self):
        assert format_price(0.0) == "0"

    def test_blank_cell_is_zero(self):
        assert format_price("") == "0"


# ---------------------------------------------------------------------------
# is_foil
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsFoil:
    def test_boolean_true(self):
        assert is_foil(True) is True

    def test_boolean_false(self):
        assert is_foil(False) is False

    def test_number_one(self):
        assert is_foil(1.0) is True

    def test_number_zero(self):
        assert is_foil(0.0) is False

    def test_text_true(self):
        assert is_foil("TRUE") is True

    def test_text_false(self):
        assert is_foil("false") is False

    def test_blank_text(self):
        assert is_foil("") is False


# ---------------------------------------------------------------------------
# convert_order_rows
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConvertOrderRows:
    def test_single_row_maps_every_column(self):
        converted, skipped, breakdown = convert_order_rows([_row()])

        assert {key: converted[0][key] for key in MOXFIELD_COLUMNS} == {
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
        }
        assert converted[0]["Source"] == "Attercop | HOB 116"
        assert skipped == []
        assert breakdown == {
            "Condition": {"Near Mint": 1},
            "Language": {"en": 1},
            "Foil": {"non-foil": 1},
        }

    def test_foil_and_collector_number_and_price(self):
        converted, _, _ = convert_order_rows(
            [
                _row(
                    **{"Foil/Reverse": True, "Collector Number": "035", "Price in EUR Cents": 85.0}
                )
            ]
        )

        assert converted[0]["Foil"] == "foil"
        assert converted[0]["Collector Number"] == "35"
        assert converted[0]["Purchase Price"] == "0.85"

    @pytest.mark.parametrize(
        ("cardtrader", "moxfield"),
        [
            ("Mint", "Mint"),
            ("Near Mint", "Near Mint"),
            ("Slightly Played", "Lightly Played"),
            ("Moderately Played", "Moderately Played"),
            ("Played", "Heavily Played"),
            ("Heavily Played", "Heavily Played"),
            ("Poor", "Damaged"),
        ],
    )
    def test_every_condition_maps(self, cardtrader, moxfield):
        converted, _, _ = convert_order_rows([_row(Condition=cardtrader)])
        assert converted[0]["Condition"] == moxfield

    def test_unknown_condition_names_the_card(self):
        with pytest.raises(ValueError, match="Attercop"):
            convert_order_rows([_row(Condition="Pristine")])

    @pytest.mark.parametrize(
        ("cardtrader", "moxfield"),
        [("jp", "ja"), ("kr", "ko"), ("cn", "zhs"), ("it", "it"), ("xx", "xx")],
    )
    def test_language_codes(self, cardtrader, moxfield):
        converted, _, _ = convert_order_rows([_row(Language=cardtrader)])
        assert converted[0]["Language"] == moxfield

    def test_non_magic_rows_are_skipped(self):
        converted, skipped, breakdown = convert_order_rows(
            [_row(), _row(Game="Pokemon", **{"Item Name": "Pikachu"})]
        )

        assert [row["Name"] for row in converted] == ["Attercop"]
        assert skipped == ["Pikachu"]
        assert breakdown["Condition"] == {"Near Mint": 1}

    def test_breakdown_counts_across_rows(self):
        _, _, breakdown = convert_order_rows(
            [
                _row(),
                _row(Condition="Slightly Played", Language="jp", **{"Foil/Reverse": True}),
                _row(**{"Foil/Reverse": True}),
            ]
        )

        assert breakdown == {
            "Condition": {"Near Mint": 2, "Lightly Played": 1},
            "Language": {"en": 2, "ja": 1},
            "Foil": {"foil": 2, "non-foil": 1},
        }

    def test_no_rows(self):
        with pytest.raises(ValueError, match="no rows"):
            convert_order_rows([])

    def test_missing_columns_are_named(self):
        row = _row()
        del row["Collector Number"]
        del row["Set Code"]

        with pytest.raises(ValueError, match="Set Code, Collector Number"):
            convert_order_rows([row])


# ---------------------------------------------------------------------------
# CardTrader quirks
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStripNameQualifier:
    @pytest.mark.parametrize(
        ("cardtrader", "moxfield"),
        [
            ("All That Glitters (Borderless)", "All That Glitters"),
            ("Spirit Link (Retro Frame)", "Spirit Link"),
            ("Lightning Bolt (Promo)", "Lightning Bolt"),
            ("Smashing Spree (856 | Tutorial 18)", "Smashing Spree"),
            ("Zombie (2/2)", "Zombie"),
        ],
    )
    def test_qualifier_is_dropped(self, cardtrader, moxfield):
        assert strip_name_qualifier(cardtrader) == moxfield

    def test_plain_name_is_untouched(self):
        assert strip_name_qualifier("Attercop") == "Attercop"

    def test_double_faced_name_is_untouched(self):
        assert strip_name_qualifier("Beorn, Reluctant Host // Till and Tend") == (
            "Beorn, Reluctant Host // Till and Tend"
        )


@pytest.mark.unit
class TestBaseSetCode:
    def test_collectors_set_loses_its_c_prefix(self):
        assert base_set_code("CDFT", "Aetherdrift Collectors") == "DFT"

    def test_ordinary_set_is_untouched(self):
        assert base_set_code("CLB", "Battle for Baldur's Gate") == "CLB"

    def test_collectors_set_without_a_c_prefix_is_untouched(self):
        assert base_set_code("MSHB", "Marvel Collectors") == "MSHB"


@pytest.mark.unit
class TestIdentifiers:
    def test_printing_identifier(self):
        entry = {"Edition": "DFT", "Collector Number": "324", "Name": "Guidelight Pathmaker"}
        assert printing_identifier(entry) == {"set": "DFT", "collector_number": "324"}

    @pytest.mark.parametrize(
        ("collector", "number"),
        [("T 4/2", "4"), ("F 22/1", "22"), ("T013", "13"), ("7/018", "7"), ("T 08/03", "8")],
    )
    def test_token_identifier_extracts_the_leading_number(self, collector, number):
        entry = {"Edition": "HOB", "Collector Number": collector, "Name": "Goblin Army"}
        assert token_identifier(entry) == {"set": "THOB", "collector_number": number}

    def test_token_identifier_needs_a_number(self):
        assert token_identifier({"Edition": "HOB", "Collector Number": "", "Name": "x"}) is None

    def test_token_identifier_needs_a_set(self):
        assert token_identifier({"Edition": "", "Collector Number": "4", "Name": "x"}) is None


@pytest.mark.unit
class TestSetCandidates:
    def test_paged_set_also_offers_its_base_code(self):
        assert set_candidates({"Edition": "PLIST2"}) == ["PLIST2", "PLIST"]

    def test_ordinary_set_offers_only_itself(self):
        assert set_candidates({"Edition": "MSHB"}) == ["MSHB"]

    def test_paged_set_with_a_longer_base_code(self):
        assert set_candidates({"Edition": "LEG2"}) == ["LEG2", "LEG"]

    @pytest.mark.parametrize("edition", ["2X2", "MH2", "M21", "J25", "MB1"])
    def test_a_set_that_merely_ends_in_a_digit_is_not_trimmed(self, edition):
        """Trimming these would leave a stub too short to be a real set code."""
        assert set_candidates({"Edition": edition}) == [edition]

    def test_missing_set_offers_nothing(self):
        assert set_candidates({"Edition": ""}) == []


@pytest.mark.unit
def test_identity_reads_as_name_set_number():
    assert identity("Spirit Link", "DMR", "274") == "Spirit Link | DMR 274"


# ---------------------------------------------------------------------------
# apply_printings
# ---------------------------------------------------------------------------


def _entry(**overrides):
    entry = {
        "Count": "1",
        "Name": "Spirit Link",
        "Edition": "DMR",
        "Condition": "Near Mint",
        "Language": "en",
        "Foil": "",
        "Collector Number": "274",
        "Alter": "",
        "Playtest Card": "",
        "Purchase Price": "0.29",
        "Source": "Spirit Link (Retro Frame) | CDMR 274",
    }
    entry.update(overrides)
    return entry


@pytest.mark.unit
class TestApplyPrintings:
    def test_scryfall_answer_replaces_the_row_identity(self):
        printing = {"name": "Spirit Link", "set": "DMR", "collector_number": "274"}

        rows, corrections, unresolved = apply_printings([_entry()], {0: printing})

        assert rows[0]["Name"] == "Spirit Link"
        assert rows[0]["Edition"] == "DMR"
        assert rows[0]["Collector Number"] == "274"
        assert corrections == [
            {"before": "Spirit Link (Retro Frame) | CDMR 274", "after": "Spirit Link | DMR 274"}
        ]
        assert unresolved == []

    def test_a_token_is_renamed_and_moved_to_its_own_set(self):
        entry = _entry(
            **{
                "Name": "Goblin Army // Human Soldier",
                "Edition": "HOB",
                "Collector Number": "T 4/2",
                "Source": "Goblin Army // Human Soldier | HOB T 4/2",
            }
        )
        printing = {"name": "Goblin Army", "set": "THOB", "collector_number": "4"}

        rows, corrections, _ = apply_printings([entry], {0: printing})

        assert rows[0]["Name"] == "Goblin Army"
        assert rows[0]["Edition"] == "THOB"
        assert rows[0]["Collector Number"] == "4"
        assert corrections[0]["after"] == "Goblin Army | THOB 4"

    def test_an_unchanged_row_is_not_reported(self):
        entry = _entry(Source="Spirit Link | DMR 274")
        printing = {"name": "Spirit Link", "set": "DMR", "collector_number": "274"}

        rows, corrections, unresolved = apply_printings([entry], {0: printing})

        assert corrections == []
        assert unresolved == []
        assert rows[0]["Name"] == "Spirit Link"

    def test_an_unresolved_row_keeps_the_rule_output_and_is_reported(self):
        entry = _entry(
            **{
                "Name": "Sapphire Charm",
                "Edition": "MB1",
                "Collector Number": "89",
                "Source": "Sapphire Charm | MB1 89",
            }
        )

        rows, corrections, unresolved = apply_printings([entry], {})

        assert rows[0]["Edition"] == "MB1"
        assert corrections == []
        assert unresolved == ["Sapphire Charm | MB1 89"]
