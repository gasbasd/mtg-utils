import pytest

from mtg_utils.commands.show_shopping_list.render import render_shopping_list


@pytest.mark.unit
def test_render_nothing_to_buy(capsys):
    """When to_buy is empty, render_shopping_list outputs the 'Nothing to buy' panel."""
    render_shopping_list([], [("Forest", 1)], 1)

    captured = capsys.readouterr()
    assert "Nothing to buy" in captured.out or "Nothing" in captured.out


@pytest.mark.unit
def test_render_purchased_card_marked(capsys):
    """Cards in purchased_names are marked with * in the available panel."""
    render_shopping_list([], [("Sol Ring", 1), ("Island", 2)], 1, purchased_names={"Sol Ring"})

    captured = capsys.readouterr()
    assert "*" in captured.out
    assert "Sol Ring" in captured.out
