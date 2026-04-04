import pytest
from click.testing import CliRunner

from mtg_utils.commands import compare_decks as compare_decks_module
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
    # With no overlap, the common-cards panel is not printed
    assert "Cards in common" not in result.output
    assert "Only in" in result.output
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
    assert "1 Lightning Bolt" in result.output  # the excess


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


@pytest.mark.integration
def test_compare_decks_rule_header(tmp_path, monkeypatch):
    """Rule header contains both filenames and the 'vs' separator."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("1 Island\n")
    (tmp_path / "b.txt").write_text("1 Forest\n")
    result = CliRunner().invoke(cli, ["compare-decks", "--deck1-file", "a.txt", "--deck2-file", "b.txt"])
    assert result.exit_code == 0
    assert "a.txt" in result.output
    assert "b.txt" in result.output
    assert "vs" in result.output


@pytest.mark.unit
def test_compare_decks_side_by_side_panels_do_not_force_height(monkeypatch):
    """Regression guard: side-by-side unique panels should use natural height."""
    panel_kwargs: list[dict] = []

    class DummyPanel:
        def __init__(self, _renderable, **kwargs):
            panel_kwargs.append(kwargs)

    def fake_read_list(path):
        return ["1 Island"] if path == "d1.txt" else ["1 Forest"]

    monkeypatch.setattr(compare_decks_module, "read_list", fake_read_list)
    monkeypatch.setattr(compare_decks_module, "Panel", DummyPanel)
    monkeypatch.setattr(compare_decks_module.console, "print", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(compare_decks_module, "side_by_side", lambda left, right: (left, right))

    callback = compare_decks_module.compare_decks.callback
    assert callback is not None
    callback("d1.txt", "d2.txt")

    unique_panel_titles = [
        kwargs.get("title", "") for kwargs in panel_kwargs if kwargs.get("title", "").startswith("Only in ")
    ]
    assert len(unique_panel_titles) == 2
    assert all("height" not in kwargs for kwargs in panel_kwargs if kwargs.get("title", "").startswith("Only in "))
