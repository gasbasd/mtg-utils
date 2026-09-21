import os
from unittest.mock import MagicMock, patch

import pytest

from mtg_utils.utils.readers import read_list, read_xls_rows

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "cardtrader_sample.xls")


@pytest.mark.unit
def test_read_list_normal(tmp_path):
    f = tmp_path / "cards.txt"
    f.write_text("1 Island\n2 Forest\n")
    assert read_list(str(f)) == ["1 Island", "2 Forest"]


@pytest.mark.unit
def test_read_list_skips_empty_lines(tmp_path):
    f = tmp_path / "cards.txt"
    f.write_text("1 Island\n\n2 Forest\n\n")
    assert read_list(str(f)) == ["1 Island", "2 Forest"]


@pytest.mark.unit
def test_read_list_strips_whitespace(tmp_path):
    f = tmp_path / "cards.txt"
    f.write_text("  1 Island  \n  2 Forest  \n")
    assert read_list(str(f)) == ["1 Island", "2 Forest"]


@pytest.mark.unit
def test_read_list_empty_file(tmp_path):
    f = tmp_path / "cards.txt"
    f.write_text("")
    assert read_list(str(f)) == []


@pytest.mark.unit
def test_read_list_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_list("/nonexistent/path/cards.txt")


@pytest.mark.unit
def test_read_xls_rows_keys_cells_by_header():
    rows = read_xls_rows(FIXTURE)

    assert len(rows) == 4
    assert rows[0]["Item Name"] == "Goblin Army // Human Soldier"
    assert rows[0]["Price in EUR Cents"] == 14.0
    assert rows[1]["Collector Number"] == "035"
    assert rows[3]["Game"] == "Pokemon"


@pytest.mark.unit
def test_read_xls_rows_empty_sheet():
    sheet = MagicMock(nrows=0)
    workbook = MagicMock()
    workbook.sheet_by_index.return_value = sheet

    with patch("mtg_utils.utils.readers.xlrd.open_workbook", return_value=workbook):
        assert read_xls_rows("whatever.xls") == []


@pytest.mark.unit
def test_read_xls_rows_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_xls_rows("/nonexistent/path/order.xls")
