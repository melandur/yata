# SPDX-License-Identifier: MIT

import pytest

from harness.fixtures import FixtureTree
from harness.modes import ALL_MODES, NEXT_ENTRY_KEY


@pytest.fixture
def fixture_tree():
    fixture = FixtureTree.create(
        {f"{index:03}.txt": f"{index}\n" for index in range(100)}
    )
    try:
        yield fixture
    finally:
        fixture.cleanup()


def visible_entries(yata):
    viewport = next(
        node.screen_bounds()
        for node in yata.entry_container().ancestors()
        if node.role == "scroll pane"
    )
    return [
        node for node in yata.entries()
        if viewport.y <= node.screen_bounds().y < viewport.y + viewport.height
    ]


@pytest.mark.parametrize("mode", ALL_MODES)
def test_background_rename_preserves_scroll_and_multiselection(yata, mode):
    yata.select_entry("001.txt")
    yata.pointer.click(yata.entry("003.txt"), modifiers=["ctrl"])
    yata.wait_for_selection(["001.txt", "003.txt"])
    before = visible_entries(yata)[0].name
    yata.pointer.scroll(at=yata.pane().screen_bounds().center, clicks=2)
    yata.wait(
        lambda: visible_entries(yata) and visible_entries(yata)[0].name != before,
        "the listing to scroll",
    )
    visible = visible_entries(yata)
    marker = yata.settle(visible[len(visible) // 2])
    scrolled = marker.screen_bounds().y

    source_name = visible[-1].name
    source = yata.fixture.path(source_name)
    destination_name = source.stem + "-renamed.txt"
    source.write_text("updated before rename\n")
    source.rename(yata.fixture.path(destination_name))
    yata.entry(destination_name)
    yata.wait_for_entry_gone(source_name)
    yata.settle(marker)

    assert marker.screen_bounds().y == scrolled
    yata.pointer.scroll(at=yata.pane().screen_bounds().center, clicks=20, down=False)
    yata.wait_for_selection(["001.txt", "003.txt"])
    assert not source.exists()
    assert yata.fixture.path(destination_name).read_text() == "updated before rename\n"


@pytest.mark.parametrize("mode", ALL_MODES)
def test_keyboard_navigation_survives_background_insertion(yata, mode):
    yata.select_entry("003.txt")
    yata.wait_for_focused_entry("003.txt")
    yata.fixture.path("000-new.txt").write_text("new entry\n")
    yata.entry("000-new.txt")
    yata.keyboard.press(NEXT_ENTRY_KEY[mode])
    yata.wait_for_focused_entry("004.txt")
    yata.wait_for_selection(["004.txt"])
