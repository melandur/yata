# SPDX-License-Identifier: MIT
"""Keyboard-only movement, activation, and multi-selection."""

from __future__ import annotations

import pytest

from harness.modes import ALL_MODES, COLUMNS_AND_ONE, NEXT_ENTRY_KEY, PREVIOUS_ENTRY_KEY

ROOT_ENTRIES = ["archive", "documents", "pictures", "readme.md", "todo.txt"]


@pytest.mark.preferences(type_to_search=False)
@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("bindings", ["arrows", "hjkl"])
def test_arrow_keys_move_focus_and_selection(yata, mode, bindings):
    assert yata.entry_names() == ROOT_ENTRIES

    # A file, so that a single click never navigates in any presentation.
    yata.select_entry("readme.md")
    yata.wait_for_focused_entry("readme.md")

    aliases = {"Left": "h", "Down": "j", "Up": "k", "Right": "l"}
    next_key = NEXT_ENTRY_KEY[mode]
    previous_key = PREVIOUS_ENTRY_KEY[mode]
    if bindings == "hjkl":
        next_key, previous_key = aliases[next_key], aliases[previous_key]
    yata.keyboard.press(next_key)
    yata.wait_for_focused_entry("todo.txt")
    yata.wait(
        lambda: yata.selected_names() == ["todo.txt"],
        "the selection to follow focus",
    )

    yata.keyboard.press(previous_key)
    yata.wait_for_focused_entry("readme.md")


@pytest.mark.preferences(arrow_navigation_scoped=True, type_to_search=False)
@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("bindings", ["arrows", "hjkl"])
def test_arrow_scope_keeps_focus_in_files_and_toggles_live(yata, mode, bindings):
    up, left = ("Up", "Left") if bindings == "arrows" else ("k", "h")
    yata.select_entry("readme.md")
    yata.keyboard.press("Home")
    yata.wait_for_focused_entry("archive")
    for key in [up, left, up]:
        yata.keyboard.press(key)
        yata.wait_for_focused_entry("archive")

    yata.keyboard.press("ctrl+\\")
    yata.wait(
        lambda: yata.environment.read_preferences().get("arrow_navigation_scoped") == "false",
        "arrow scope disabled by shortcut",
    )
    yata.keyboard.press(up)
    yata.wait(lambda: yata.focused_name() is None, "Up leaves the file list")
    yata.keyboard.press("Down")
    yata.wait_for_focused_entry("archive")
    yata.keyboard.press("ctrl+\\")
    yata.wait(
        lambda: yata.environment.read_preferences().get("arrow_navigation_scoped") == "true",
        "arrow scope enabled by shortcut",
    )
    yata.keyboard.press(up)
    yata.wait_for_focused_entry("archive")


@pytest.mark.parametrize("mode", COLUMNS_AND_ONE)
def test_alt_up_and_history_navigate_between_directories(yata, mode):
    root = yata.fixture.root.name

    yata.open_directory("documents")
    yata.keyboard.press("alt+Up")
    yata.wait_for_directory(root)

    yata.keyboard.press("alt+Left")
    yata.wait_for_directory("documents")

    yata.keyboard.press("alt+Right")
    yata.wait_for_directory(root)


@pytest.mark.preferences(browser_mode="list")
@pytest.mark.parametrize("return_key", ["alt+Left", "alt+Up"])
@pytest.mark.parametrize("enter_with", ["keyboard", "pointer"])
def test_list_return_restores_nested_scroll_selection_and_keyboard_cursor(
    yata, return_key, enter_with
):
    def populate(parent):
        for index in range(160):
            (parent / f"folder-{index:03}").mkdir()

    def scroll_and_enter(parent, clicks):
        container = yata.entry_container()
        viewport = next(
            node.screen_bounds()
            for node in container.ancestors()
            if node.role == "scroll pane"
        )
        yata.pointer.scroll(at=viewport.center, clicks=clicks)

        def middle_entry():
            visible = [
                node for node in yata.entries()
                if viewport.y < node.screen_bounds().y
                < viewport.y + viewport.height - node.screen_bounds().height
            ]
            if visible and visible[0].name != "folder-000":
                return visible[len(visible) // 2]
            return None

        marker = yata.wait(middle_entry, "a scrolled directory viewport")
        name = marker.name
        populate(parent / name)
        yata.select_entry(name)
        yata.wait_for_focused_entry(name)
        y = yata.settle(yata.entry(name)).screen_bounds().y
        if enter_with == "keyboard":
            yata.keyboard.press("Return")
        else:
            yata.open_directory(name)
        yata.wait_for_directory(name)
        return name, y

    parent = yata.fixture.path("archive")
    populate(parent)
    yata.open_directory("archive")
    first, first_y = scroll_and_enter(parent, 18)
    second, second_y = scroll_and_enter(parent / first, 10)

    for directory, name, y in [(first, second, second_y), ("archive", first, first_y)]:
        yata.keyboard.press(return_key)
        yata.wait_for_directory(directory)
        yata.wait_for_selection([name])
        yata.wait_for_focused_entry(name)
        restored = yata.settle(yata.entry(name))
        assert abs(restored.screen_bounds().y - y) <= 2, "restore the viewport, not just reveal the selection"
        next_name = f"folder-{int(name.removeprefix('folder-')) + 1:03}"
        yata.keyboard.press("Down")
        yata.wait_for_focused_entry(next_name)
        yata.wait_for_selection([next_name])


@pytest.mark.parametrize("mode", ALL_MODES)
def test_shift_arrow_extends_the_selection(yata, mode):
    yata.select_entry("readme.md")
    yata.wait_for_focused_entry("readme.md")

    yata.keyboard.press(f"shift+{NEXT_ENTRY_KEY[mode]}")

    yata.wait(
        lambda: yata.selected_names() == ["readme.md", "todo.txt"],
        "shift and an arrow to extend the selection",
    )

    yata.keyboard.press(f"shift+{PREVIOUS_ENTRY_KEY[mode]}")
    yata.wait(
        lambda: yata.selected_names() == ["readme.md"],
        "shift and the opposite arrow to shrink the selection again",
    )


@pytest.mark.parametrize("mode", COLUMNS_AND_ONE)
def test_select_all_selects_every_entry(yata, mode):
    yata.select_entry("readme.md")

    yata.keyboard.press("ctrl+a")

    yata.wait(
        lambda: yata.selected_names() == ROOT_ENTRIES,
        "Ctrl+A to select every entry in the pane",
    )


def test_focus_stays_usable_after_changing_views(yata):
    yata.select_entry("readme.md")
    yata.wait_for_focused_entry("readme.md")

    yata.keyboard.press("ctrl+3")
    yata.wait_for_view("List")

    yata.wait_for_focused_entry("readme.md")
    yata.keyboard.press("Down")
    yata.wait_for_focused_entry("todo.txt")

    yata.keyboard.press("ctrl+1")
    yata.wait_for_view("Columns")
    yata.keyboard.press("Up")
    yata.wait_for_focused_entry("readme.md")


def test_keyboard_only_copy_and_paste_round_trip(yata):
    """A complete file operation without ever touching the pointer."""

    fixture = yata.fixture
    yata.keyboard.press("Down")
    yata.wait(lambda: yata.focused_name() is not None, "initial keyboard focus")

    yata.keyboard.press("End")
    yata.wait_for_focused_entry("todo.txt")
    yata.keyboard.press("ctrl+c")

    yata.keyboard.press("Home")
    yata.wait_for_focused_entry("archive")
    yata.keyboard.press("Return")
    yata.wait_for_directory("archive")
    yata.keyboard.press("ctrl+v")

    yata.wait(
        lambda: fixture.path("archive/todo.txt").exists(),
        "the keyboard-only paste to land",
    )
    assert fixture.path("todo.txt").exists(), "a copy must leave the source alone"
