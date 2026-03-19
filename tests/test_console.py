import pytest

from mtg_utils.utils.console import _StderrProxy, _StdoutProxy, console, err_console


@pytest.mark.unit
def test_stdout_proxy_write(capsys):
    proxy = _StdoutProxy()
    proxy.write("hello")
    captured = capsys.readouterr()
    assert "hello" in captured.out


@pytest.mark.unit
def test_stdout_proxy_flush():
    proxy = _StdoutProxy()
    proxy.flush()  # should not raise


@pytest.mark.unit
def test_stdout_proxy_isatty():
    proxy = _StdoutProxy()
    result = proxy.isatty()
    assert isinstance(result, bool)


@pytest.mark.unit
def test_stdout_proxy_encoding():
    proxy = _StdoutProxy()
    assert isinstance(proxy.encoding, str)


@pytest.mark.unit
def test_stdout_proxy_errors():
    proxy = _StdoutProxy()
    assert isinstance(proxy.errors, str)


@pytest.mark.unit
def test_stderr_proxy_write(capsys):
    proxy = _StderrProxy()
    proxy.write("err!")
    captured = capsys.readouterr()
    assert "err!" in captured.err


@pytest.mark.unit
def test_stderr_proxy_flush():
    proxy = _StderrProxy()
    proxy.flush()  # should not raise


@pytest.mark.unit
def test_stderr_proxy_isatty():
    proxy = _StderrProxy()
    result = proxy.isatty()
    assert isinstance(result, bool)


@pytest.mark.unit
def test_stderr_proxy_encoding():
    proxy = _StderrProxy()
    assert isinstance(proxy.encoding, str)


@pytest.mark.unit
def test_stderr_proxy_errors():
    proxy = _StderrProxy()
    assert isinstance(proxy.errors, str)


@pytest.mark.unit
def test_console_and_err_console_exist():
    from rich.console import Console

    assert isinstance(console, Console)
    assert isinstance(err_console, Console)
