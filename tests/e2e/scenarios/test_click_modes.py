# SPDX-License-Identifier: MIT
"""Single-click and double-click activation, and switching between them."""

from __future__ import annotations

import pytest

from harness.modes import ALL_MODES

SINGLE_CLICK = pytest.mark.preferences(
    list_folder_clicks=1, list_file_clicks=1,
    grid_folder_clicks=1, grid_file_clicks=1,
    explorer_folder_clicks=1, explorer_file_clicks=1,
)
DOUBLE_CLICK = pytest.mark.preferences(
    list_folder_clicks=2, list_file_clicks=2,
    grid_folder_clicks=2, grid_file_clicks=2,
    explorer_folder_clicks=2, explorer_file_clicks=2,
)


@SINGLE_CLICK
@pytest.mark.parametrize("mode", ALL_MODES)
def test_single_click_opens_a_directory(yata, mode):
    yata.pointer.click(yata.entry("documents"))

    yata.wait(
        lambda: yata.pane().name == "documents",
        "one click to open the directory in single-click mode",
    )
    yata.entry("notes.txt")
    yata.wait_for_selection([], "documents")


@SINGLE_CLICK
@pytest.mark.parametrize("mode", ALL_MODES)
def test_keyboard_open_selects_the_first_child(yata, mode):
    yata.select_entry_with_keyboard("documents")
    yata.keyboard.press("Return")
    yata.wait_for_directory("documents")
    yata.wait_for_selection(["notes.txt"], "documents")


@SINGLE_CLICK
@pytest.mark.parametrize("activation", ["mouse", "keyboard"])
def test_sidebar_selection_depends_on_activation(yata, activation):
    home = yata.environment.home
    (home / "child").mkdir()
    if activation == "mouse":
        yata.pointer.click(yata.sidebar_button("Home"))
    else:
        yata.keyboard.press("Home")
        yata.keyboard.press("Left")
        yata.wait(
            lambda: yata.sidebar_button("Home").has_state("focused"),
            "keyboard focus on the Home sidebar button",
        )
        yata.keyboard.press("Return")
    yata.wait_for_directory(home.name)
    yata.entry("child", home.name)
    yata.wait_for_selection(["child"] if activation == "keyboard" else [], home.name)


@SINGLE_CLICK
@pytest.mark.parametrize("mode", ALL_MODES)
def test_keyboard_selection_still_works_in_single_click_mode(yata, mode):
    yata.keyboard.press("Down")
    yata.wait(lambda: yata.focused_name() is not None, "keyboard focus")
    focused = yata.focused_name()

    yata.wait(
        lambda: yata.selected_names() == [focused],
        "the keyboard to select without opening anything",
    )
    assert yata.pane().name == yata.fixture.root.name, (
        "moving the keyboard cursor must not navigate in single-click mode"
    )


@DOUBLE_CLICK
@pytest.mark.parametrize("mode", ALL_MODES)
def test_one_click_only_selects_in_double_click_mode(yata, mode):
    root = yata.fixture.root.name

    yata.pointer.click(yata.entry("documents"))

    yata.wait(
        lambda: yata.selected_names() == ["documents"],
        "one click to select in double-click mode",
    )
    assert yata.pane().name == root, "one click must not open the directory"


@DOUBLE_CLICK
@pytest.mark.parametrize("mode", ALL_MODES)
def test_two_clicks_open_in_double_click_mode(yata, mode):
    yata.pointer.double_click(yata.entry("documents"))

    yata.wait(
        lambda: yata.pane().name == "documents",
        "two clicks to open the directory",
    )
    yata.entry("notes.txt")
    yata.wait_for_selection([], "documents")


@DOUBLE_CLICK
@pytest.mark.parametrize("mode", ALL_MODES)
def test_two_slow_clicks_do_not_open(yata, mode):
    """Two clicks outside the double-click interval are two single clicks."""

    root = yata.fixture.root.name

    yata.pointer.click_twice_slowly(yata.entry("documents"))

    yata.wait(
        lambda: yata.selected_names() == ["documents"],
        "the entry to stay selected",
    )
    assert yata.pane().name == root


@DOUBLE_CLICK
@pytest.mark.preferences(browser_mode="list")
def test_changing_the_preference_takes_effect_without_restarting(yata):
    root = yata.fixture.root.name
    yata.pointer.click(yata.entry("documents"))
    yata.wait(
        lambda: yata.selected_names() == ["documents"],
        "double-click mode to only select",
    )
    assert yata.pane().name == root

    _choose_single_click(yata)

    yata.pointer.click(yata.entry("pictures"))
    yata.wait(
        lambda: yata.pane().name == "pictures",
        "the new preference to apply to the running window",
    )


def _choose_single_click(yata) -> None:
    """Switch the List view to single-click activation through Settings."""

    yata.pointer.click(yata.header_button("Settings"))
    option = yata.wait(
        lambda: yata.window.find(
            role="toggle button", name="List view Folders Single", rendered=False
        ),
        "the List single-click option in Settings",
    )
    assert option.activate(), "the option should expose an accessible action"
    yata.wait(
        lambda: yata.environment.read_preferences().get("explorer_folder_clicks")
        == "1",
        "the single-click choice to be saved",
    )
    yata.keyboard.press("Escape")
    yata.wait(
        lambda: yata.window.find(
            role="toggle button", name="List view Folders Single"
        )
        is None,
        "Settings to close",
    )
