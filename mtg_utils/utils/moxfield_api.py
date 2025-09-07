import cloudscraper

scraper = cloudscraper.create_scraper()

def library_sort_key(card_entry):
    # Extract the card name (everything after the first space)
    card_name = card_entry.split(' ', 1)[1]
    
    # Check if it's one of the snow-covered lands to put at the end
    snow_lands = [
        "Snow-Covered Forest",
        "Snow-Covered Island",
        "Snow-Covered Mountain",
        "Snow-Covered Plains",
        "Snow-Covered Swamp",
    ]
    if card_name in snow_lands:
        return (1, card_name)  # Group 1 (at end) and then alphabetically
    else:
        return (0, card_name) 


def get_deck_list(deck_id: str) -> list[str]:
    """Fetch a deck list from Moxfield by its ID."""
    response = scraper.get(f"https://api2.moxfield.com/v3/decks/all/{deck_id}")
    response.raise_for_status()  # Raise an error for bad responses

    deck_list = []
    data = response.json()
    for card in data["boards"]["mainboard"]["cards"].values():
        quantity = card["quantity"]
        name = card["card"]["name"]
        deck_list.append(f"{quantity} {name}")
    deck_list.sort()
    commanders = data["boards"]['commanders']['cards'].values()
    for i, commander in enumerate(commanders):
        name = commander["card"]["name"]
        deck_list.insert(i, f"1 {name}")

    return deck_list

def get_library(binder_id: str) -> list[str]:
    """Fetch the library cards from Moxfield."""
    first_page = scraper.get(f"https://api2.moxfield.com/v1/trade-binders/{binder_id}/search?pageNumber=1&pageSize=100")
    first_page.raise_for_status()  # Raise an error for bad responses
    first_page_data = first_page.json()
    total_pages = first_page_data["totalPages"]
    total_data = first_page_data["data"]
    for page_number in range(2, total_pages + 1):
        response = scraper.get(f"https://api2.moxfield.com/v1/trade-binders/{binder_id}/search?pageNumber={page_number}&pageSize=100")
        response.raise_for_status()
        total_data += response.json()["data"]
    card_quantities = {}
    for card in total_data:
        quantity = card["quantity"]
        name = card["card"]["name"]
        if name in card_quantities:
            card_quantities[name] += quantity
        else:
            card_quantities[name] = quantity
    
    library = [f"{quantity} {name}" for name, quantity in card_quantities.items()]
    library.sort(key=library_sort_key)
    return library
