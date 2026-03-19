import json
import pytest


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Chdir to tmp_path and return a make_config callable.

    Usage::

        def test_something(repo):
            cfg = repo(binder_id="abc", decks={"my_deck": {"id": "x", "file": "card_library/decks/my_deck.txt"}})
    """
    monkeypatch.chdir(tmp_path)

    def make_config(binder_id="test-binder", decks=None, purchased_file="card_library/purchased.txt"):
        config = {
            "binder_id": binder_id,
            "decks": decks or {},
            "purchased_file": purchased_file,
        }
        (tmp_path / "card_library").mkdir(exist_ok=True)
        (tmp_path / "card_library" / "decks").mkdir(exist_ok=True)
        (tmp_path / "config.json").write_text(json.dumps(config))
        return config

    return make_config
