from typing import NamedTuple

from rich.markup import escape

from mtg_utils.utils.cards import parse_card_list
from mtg_utils.utils.config import DeckConfig
from mtg_utils.utils.console import err_console


class DeckFetchResult(NamedTuple):
    name: str
    ok: bool
    file: str
    cards: list[str]
    config: DeckConfig


def _compute_card_usage(
    library_dict: dict[str, int],
    deck_cards: dict[str, dict[str, int]],
    decks: list[tuple[str, list[str], DeckConfig]],
) -> tuple[dict[str, int], dict[str, list[tuple[str, str]]], dict[str, DeckConfig]]:
    """Compute library consumption and flag unavailable cards.

    Returns:
        used_cards: {card_name: total qty consumed from the library pool}
        unavailable_cards: {deck_name: [(card_name, human-readable message)]}
        deck_configs: {deck_name: deck config dict}
    """
    used_cards: dict[str, int] = {}
    card_usage_by_deck: dict[str, dict[str, int]] = {}
    unavailable_cards: dict[str, list[tuple[str, str]]] = {}
    deck_configs: dict[str, DeckConfig] = {deck_name: deck_config for deck_name, _, deck_config in decks}

    incremental_shared_cache: dict[tuple[str, str], int] = {}

    def _incremental_shared_quantity(deck_name: str, card_name: str, stack: tuple[str, ...] = ()) -> int:
        """Return a deck's non-overlapping reusable quantity for a card.

        This quantity represents only the deck's additional copies after applying its
        own shared_decks. Using this for downstream sharing avoids double-counting
        when shared decks overlap through the same dependency chain.
        """
        cache_key = (deck_name, card_name)
        if cache_key in incremental_shared_cache:
            return incremental_shared_cache[cache_key]

        deck_quantity = deck_cards.get(deck_name, {}).get(card_name, 0)
        if deck_quantity <= 0:
            incremental_shared_cache[cache_key] = 0
            return 0

        if deck_name in stack:
            err_console.print(
                f"[yellow]⚠[/yellow] WARNING: Circular shared deck reference detected for "
                f"'{escape(deck_name)}' while resolving '{escape(card_name)}'"  # pragma: no cover
            )
            incremental_shared_cache[cache_key] = deck_quantity
            return deck_quantity

        cfg = deck_configs.get(deck_name)
        shared_total = 0
        if cfg:
            next_stack = (*stack, deck_name)
            for shared_deck_name in cfg.shared_decks:
                if shared_deck_name in deck_cards:
                    shared_total += _incremental_shared_quantity(shared_deck_name, card_name, next_stack)

        incremental = max(0, deck_quantity - shared_total)
        incremental_shared_cache[cache_key] = incremental
        return incremental

    for deck_name, deck, deck_config in decks:
        deck_unavailable: list[tuple[str, str]] = []
        shared_decks: list[str] = deck_config.shared_decks

        for shared_deck_name in shared_decks:
            if shared_deck_name not in deck_cards:
                err_console.print(
                    f"[yellow]⚠[/yellow] WARNING: Deck '{escape(deck_name)}' references "
                    f"non-existent shared deck '{escape(shared_deck_name)}'"  # pragma: no cover
                )

        for card_name, quantity in parse_card_list(deck).items():
            shared_quantity = 0
            shared_details: list[str] = []
            for shared_deck_name in shared_decks:
                if shared_deck_name in deck_cards:
                    deck_has = _incremental_shared_quantity(shared_deck_name, card_name)
                    if deck_has > 0:
                        shared_details.append(f"{deck_has} in {shared_deck_name}")
                        shared_quantity += deck_has

            quantity_to_consume = max(0, quantity - shared_quantity)

            total_in_library = library_dict.get(card_name, 0)
            already_used = used_cards.get(card_name, 0)
            available_quantity = total_in_library - already_used

            if available_quantity < quantity_to_consume:
                msg = f"{quantity} {card_name} (have {total_in_library}"
                if shared_details:
                    msg += f", sharing: {', '.join(shared_details)}"
                if already_used > 0 and card_name in card_usage_by_deck:
                    decks_using = ", ".join(
                        f"{q} in {dn}" for dn, q in card_usage_by_deck[card_name].items()
                    )  # pragma: no cover
                    msg += f", already used: {decks_using}"  # pragma: no cover
                msg += ")"
                deck_unavailable.append((card_name, msg))

            if quantity_to_consume > 0:
                used_cards[card_name] = used_cards.get(card_name, 0) + quantity_to_consume
                card_usage_by_deck.setdefault(card_name, {})[deck_name] = quantity_to_consume

        if deck_unavailable:
            unavailable_cards[deck_name] = deck_unavailable

    return used_cards, unavailable_cards, deck_configs
