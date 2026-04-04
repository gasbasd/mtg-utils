# Tech Context

## Technologies Used

| Component | Technology | Version/Note |
|-----------|------------|--------------|
| Python | CPython | >=3.13 |
| CLI Framework | Click | Latest stable |
| HTTP Requests | Requests + Cloudscraper | For Moxfield API |
| Data Validation | Pydantic | V2 |
| Console Output | Rich | For formatted output |
| Testing | pytest + pytest-cov | 100% coverage target |
| Linting | Ruff + Pyright | Code quality |

## Development Setup

### Prerequisites

- Python 3.13+
- Poetry (recommended) or pip

### Installation (Poetry)

```bash
git clone https://github.com/gasbasd/mtg-utils.git
cd mtg-utils
poetry install
poetry shell
```

### Installation (pip)

```bash
git clone https://github.com/gasbasd/mtg-utils.git
cd mtg-utils
pip install -e .
```

## Technical Constraints

1. **Python Version**: Must support Python 3.13+
2. **CLI**: Must be usable without GUI
3. **API**: Must handle Moxfield's anti-bot protection (Cloudscraper)
4. **Testing**: Target 100% coverage

## Tool Usage Patterns

### Running Tests

```bash
poetry run pytest
poetry run pytest tests/test_commands/test_check_missing_cards.py
poetry run pytest --cov=mtg_utils
```

### Linting

```bash
poetry run ruff check .
poetry run pyright
```

### Formatting

```bash
poetry run ruff format .
```

## Dependencies

### Core Dependencies

- click>=8.0.0
- requests>=2.28.0
- cloudscraper>=1.2.71
- pydantic>=2.0.0
- rich>=13.0.0

### Dev Dependencies

- pytest>=7.0.0
- pytest-cov>=4.0.0
- ruff>=0.1.0
- pyright>=1.1.0
