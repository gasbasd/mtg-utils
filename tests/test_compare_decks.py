import pytest
from click.testing import CliRunner
from mtg_utils.main import cli


def _write(path, lines):
    path.write_text("\n".join(lines) + "\n")


@pytest.mark.integration
def test_compare_decks_no_overlap(tmp_path):
    d1, d2 = tmp_path / "d1.txt", tmp_path / "d2.txt"
    _write(d1, ["1 Lightning Bolt"])
    _write(d2, ["1 Forest"])
    result = CliRunner().invoke(cli, ["compare-decks", "--deck1-file", str(d1), "--deck2-file", str(d2)])
    assert result.exit_code == 0
    assert "Cards in common: 0 (0 unique)" in result.output
    assert "Lightning Bolt" in result.output
    assert "Forest" in result.output



@pytest.mark.integration
def test_compare_decks_identical_decks(tmp_path):
    d1, d2 = tmp_path / "d1.txt", tmp_path / "d2.txt"
    _write(d1, ["2 Lightning Bolt", "1 Island"])
    _write(d2, ["2 Lightning Bolt", "1 Island"])
    result = CliRunner().invoke(cli, ["compare-decks", "--deck1-file", str(d1), "--deck2-file", str(d2)])
    assert result.exit_code == 0
    assert "Cards in common: 3 (2 unique)" in result.output



@pytest.mark.integration
def test_compare_decks_partial_quantity_overlap(tmp_path):
    d1, d2 = tmp_path / "d1.txt", tmp_path / "d2.txt"
    _write(d1, ["3 Lightning Bolt"])
    _write(d2, ["2 Lightning Bolt"])
    result = CliRunner().invoke(cli, ["compare-decks", "--deck1-file", str(d1), "--deck2-file", str(d2)])
    assert result.exit_code == 0
    # 2 shared, 1 only in d1
    assert "Cards in common: 2 (1 unique)" in result.output
    assert "1 Lightning Bolt" in result.output   # the excess



@pytest.mark.integration
def test_compare_decks_mixed(tmp_path):
    d1, d2 = tmp_path / "d1.txt", tmp_path / "d2.txt"
    _write(d1, ["2 Lightning Bolt", "1 Island"])
    _write(d2, ["1 Lightning Bolt", "1 Forest"])
    result = CliRunner().invoke(cli, ["compare-decks", "--deck1-file", str(d1), "--deck2-file", str(d2)])
    assert result.exit_code == 0
    assert "Cards in common: 1 (1 unique)" in result.output
    assert "Lightning Bolt" in result.output
    assert "Island" in result.output
    assert "Forest" in result.output



@pytest.mark.integration
def test_compare_decks_deck2_excess(tmp_path):
    """deck2 has MORE copies of a shared card than deck1 — covers the qty2 > common_qty branch."""
    d1, d2 = tmp_path / "d1.txt", tmp_path / "d2.txt"
    _write(d1, ["1 Island"])
    _write(d2, ["3 Island"])
    result = CliRunner().invoke(cli, ["compare-decks", "--deck1-file", str(d1), "--deck2-file", str(d2)])
    assert result.exit_code == 0
    # 1 shared, 2 only in deck2
    assert "Cards in common: 1 (1 unique)" in result.output
    assert "2 Island" in result.output
