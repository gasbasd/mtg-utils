import pytest

from mtg_utils.utils.console import console, err_console


@pytest.mark.unit
def test_console_and_err_console_exist():
    from rich.console import Console

    assert isinstance(console, Console)
    assert isinstance(err_console, Console)


@pytest.mark.unit
def test_console_writes_to_stdout(capsys):
    console.print("hello-stdout")
    captured = capsys.readouterr()
    assert "hello-stdout" in captured.out


@pytest.mark.unit
def test_err_console_writes_to_stderr(capsys):
    err_console.print("hello-stderr")
    captured = capsys.readouterr()
    assert "hello-stderr" in captured.err
