import pytest
from mtg_utils.utils.readers import read_list


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
