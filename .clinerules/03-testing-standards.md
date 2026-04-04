---
description: Testing standards and best practices for mtg-utils
author: Simone Gasbarroni
version: 1.0
tags: ["testing", "pytest", "coverage"]
---

# Testing Standards

## Overview

mtg-utils uses pytest for testing with a 100% coverage requirement. This document outlines the testing standards and practices for the project.

---

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configurations
├── test_main.py             # CLI entry point tests
├── test_config.py           # Configuration loading tests
├── test_console.py          # Console output tests
├── test_moxfield_api.py     # API integration tests
├── test_compare_decks.py    # Deck comparison tests
├── test_list_decks.py       # List decks tests
├── test_readers.py          # File reading utilities tests
├── test_commands/           # Command-specific tests
│   ├── test_check_missing_cards.py
│   └── test_update_card_library.py
└── test_utils/              # Utility module tests
    ├── test_cards.py
    ├── test_config.py
    ├── test_moxfield_api.py
    └── test_readers.py
```

---

## Test Types

### Unit Tests

- Pure logic tests, no file I/O or network mocking
- Mark with `@pytest.mark.unit`
- Focus on isolated function/class behavior

### Integration Tests

- CLI runner + filesystem + mocks
- Mark with `@pytest.mark.integration`
- Test end-to-end workflows

---

## Coverage Requirements

- **Target**: 100% coverage
- Configured in `pyproject.toml`:

```toml
[tool.coverage.report]
fail_under = 100
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
]
```

---

## Writing Good Tests

### Use Fixtures

Utilize `conftest.py` fixtures to avoid duplication:

```python
def test_something(repo):
    cfg = repo(binder_id="abc", decks={"my_deck": {"id": "x", "file": "card_library/decks/my_deck.txt"}})
```

### Mock External Dependencies

Use `monkeypatch` or `unittest.mock` for API calls:

```python
from unittest.mock import patch

@patch("requests.get")
def test_api_call(mock_get):
