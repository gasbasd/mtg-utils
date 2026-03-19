import io
import sys

from rich.console import Console


class _StdoutProxy(io.RawIOBase):
    """Delegates to the current sys.stdout so CliRunner can capture output."""

    def write(self, text: str) -> int:  # type: ignore[override]
        return sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()

    def isatty(self) -> bool:
        return getattr(sys.stdout, "isatty", lambda: False)()

    @property
    def encoding(self) -> str:
        return getattr(sys.stdout, "encoding", "utf-8")

    @property
    def errors(self) -> str:
        return getattr(sys.stdout, "errors", "replace")


class _StderrProxy(io.RawIOBase):
    """Delegates to the current sys.stderr so CliRunner can capture error output."""

    def write(self, text: str) -> int:  # type: ignore[override]
        return sys.stderr.write(text)

    def flush(self) -> None:
        sys.stderr.flush()

    def isatty(self) -> bool:
        return getattr(sys.stderr, "isatty", lambda: False)()

    @property
    def encoding(self) -> str:
        return getattr(sys.stderr, "encoding", "utf-8")

    @property
    def errors(self) -> str:
        return getattr(sys.stderr, "errors", "replace")


console = Console(file=_StdoutProxy())
err_console = Console(file=_StderrProxy())
