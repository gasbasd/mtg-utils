import pytest
from unittest.mock import patch, MagicMock
from mtg_utils.utils.moxfield_api import library_sort_key, get_deck_list, get_library


# --- library_sort_key ---

@pytest.mark.unit
def test_library_sort_key_normal_card():
    assert library_sort_key("1 Lightning Bolt") == (0, "Lightning Bolt")


@pytest.mark.unit
def test_library_sort_key_normal_card_quantity_irrelevant():
    assert library_sort_key("4 Forest") == (0, "Forest")


@pytest.mark.unit
def test_library_sort_key_snow_covered_forest():
    assert library_sort_key("1 Snow-Covered Forest") == (1, "Snow-Covered Forest")


@pytest.mark.unit
def test_library_sort_key_all_snow_lands_in_group_1():
    for land in [
        "Snow-Covered Forest",
        "Snow-Covered Island",
        "Snow-Covered Mountain",
        "Snow-Covered Plains",
        "Snow-Covered Swamp",
    ]:
        assert library_sort_key(f"2 {land}")[0] == 1


@pytest.mark.unit
def test_library_sort_key_snow_sorts_after_normal():
    normal = library_sort_key("1 Atraxa")
    snow = library_sort_key("1 Snow-Covered Island")
    assert normal < snow


# --- get_deck_list ---

def _deck_response(mainboard_cards, commanders=None):
    mock = MagicMock()
    mock.json.return_value = {
        "boards": {
            "mainboard": {"cards": mainboard_cards},
            "commanders": {"cards": commanders or {}},
        }
    }
    return mock


@pytest.mark.unit
def test_get_deck_list_returns_cards():
    response = _deck_response({
        "a": {"quantity": 2, "card": {"name": "Lightning Bolt"}},
        "b": {"quantity": 1, "card": {"name": "Island"}},
    })
    with patch("mtg_utils.utils.moxfield_api.scraper.get", return_value=response):
        result = get_deck_list("fake-id")
    assert "2 Lightning Bolt" in result
    assert "1 Island" in result


@pytest.mark.unit
def test_get_deck_list_commander_inserted_first():
    response = _deck_response(
        mainboard_cards={"a": {"quantity": 1, "card": {"name": "Lightning Bolt"}}},
        commanders={"c": {"card": {"name": "Atraxa, Praetors' Voice"}}},
    )
    with patch("mtg_utils.utils.moxfield_api.scraper.get", return_value=response):
        result = get_deck_list("fake-id")
    assert result[0] == "1 Atraxa, Praetors' Voice"


@pytest.mark.unit
def test_get_deck_list_empty_deck():
    response = _deck_response(mainboard_cards={})
    with patch("mtg_utils.utils.moxfield_api.scraper.get", return_value=response):
        result = get_deck_list("fake-id")
    assert result == []


# --- get_library ---

def _library_response(data, total_pages=1):
    mock = MagicMock()
    mock.json.return_value = {"totalPages": total_pages, "data": data}
    return mock


@pytest.mark.unit
def test_get_library_single_page():
    page = _library_response([
        {"quantity": 3, "card": {"name": "Island"}},
        {"quantity": 1, "card": {"name": "Forest"}},
    ])
    with patch("mtg_utils.utils.moxfield_api.scraper.get", return_value=page):
        result = get_library("fake-binder")
    assert "3 Island" in result
    assert "1 Forest" in result


@pytest.mark.unit
def test_get_library_aggregates_duplicate_card_names():
    page = _library_response([
        {"quantity": 2, "card": {"name": "Island"}},
        {"quantity": 3, "card": {"name": "Island"}},
    ])
    with patch("mtg_utils.utils.moxfield_api.scraper.get", return_value=page):
        result = get_library("fake-binder")
    assert "5 Island" in result
    assert len(result) == 1


@pytest.mark.unit
def test_get_library_multi_page():
    page1 = _library_response([{"quantity": 1, "card": {"name": "Forest"}}], total_pages=2)
    page2 = _library_response([{"quantity": 2, "card": {"name": "Island"}}], total_pages=2)
    with patch("mtg_utils.utils.moxfield_api.scraper.get", side_effect=[page1, page2]):
        result = get_library("fake-binder")
    assert "1 Forest" in result
    assert "2 Island" in result


@pytest.mark.unit
def test_get_library_snow_lands_sorted_last():
    page = _library_response([
        {"quantity": 1, "card": {"name": "Snow-Covered Island"}},
        {"quantity": 1, "card": {"name": "Atraxa, Praetors' Voice"}},
    ])
    with patch("mtg_utils.utils.moxfield_api.scraper.get", return_value=page):
        result = get_library("fake-binder")
    # Atraxa (group 0) must come before Snow-Covered Island (group 1)
    assert result.index("1 Atraxa, Praetors' Voice") < result.index("1 Snow-Covered Island")
