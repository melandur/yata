# SPDX-License-Identifier: MIT
"""Switching between the Columns, Icons, and List presentations."""

from __future__ import annotations

import pytest

MODES = ["Columns", "Icons", "List"]
MODE_SHORTCUTS = {"Columns": "ctrl+1", "Icons": "ctrl+2", "List": "ctrl+3"}
STORED_MODES = {"Columns": '"columns"', "Icons": '"icons"', "List": '"list"'}


@pytest.mark.parametrize("mode", ["Icons", "List"])
def test_appearance_menu_switches_presentation(yata, mode):
    assert yata.view_mode() == "Columns"
    directory = yata.fixture.root.name

    yata.switch_view(mode)

    assert yata.view_mode() == mode
    assert yata.pane().name == directory
    assert "documents" in yata.entry_names()
    yata.wait(
        lambda: yata.environment.read_preferences().get("browser_mode")
        == STORED_MODES[mode],
        "the chosen view to be written to settings.toml",
    )


def test_shortcut_round_trip_preserves_selection_and_updates_the_appearance_menu(yata):
    yata.select_entry("todo.txt")
    for mode in ["Icons", "List", "Columns"]:
        yata.keyboard.press(MODE_SHORTCUTS[mode])
        yata.wait_for_view(mode)
        assert yata.pane_names()[0] == yata.fixture.root.name
        assert "documents" in yata.entry_names()
        yata.wait(
            lambda: "todo.txt" in yata.all_selected_names(),
            f"the selection to survive the switch to {mode}",
        )

        yata.open_appearance_menu()
        for candidate in MODES:
            option = yata.window.find(role="button", name=candidate)
            assert option is not None
            assert _has_check_mark(option) == (candidate == mode), (mode, candidate)
        grouping = yata.window.find(role="button", name="Group by file type")
        assert grouping is not None
        assert ("sensitive" in grouping.states) == (mode == "List")
        yata.keyboard.press("Escape")
        yata.wait(
            lambda: yata.window.find(role="button", name="Columns") is None,
            "the appearance menu to close",
        )


def test_switching_preserves_directory_selection_and_sort(yata):
    yata.select_entry("pictures")
    ascending = yata.entry_names("pictures")
    assert ascending == ["diagram.txt", "photo.txt"]

    yata.pointer.move_to(*yata.pane("pictures").screen_bounds().center)
    reverse_sort = yata.wait(
        lambda: yata.pane("pictures").find(
            role="button", name="Ascending — click to reverse"
        ),
        "the hovered pane's sort action to appear",
    )
    yata.pointer.click(reverse_sort)
    yata.wait(
        lambda: yata.entry_names("pictures") == list(reversed(ascending)),
        "the open pane to sort descending",
    )
    yata.select_entry("diagram.txt", directory="pictures")

    yata.keyboard.press(MODE_SHORTCUTS["List"])
    yata.wait_for_view("List")

    assert yata.pane().name == "pictures", (
        "switching should land on the directory the Columns view had open"
    )
    assert yata.entry_names() == list(reversed(ascending)), (
        "the descending sort should survive the switch"
    )
    yata.wait(
        lambda: yata.selected_names() == ["diagram.txt"],
        "the selection to survive the switch",
    )
    yata.wait_for_focused_entry("diagram.txt")


def test_switching_preserves_the_pane_filter(yata):
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    yata.keyboard.type_text("todo")
    yata.wait(lambda: field.text == "todo", "the filter query to be typed")
    yata.wait(
        lambda: yata.matches() == ["todo.txt"],
        "the filter to narrow the listing",
    )

    for mode in ["Icons", "List", "Columns"]:
        yata.keyboard.press(MODE_SHORTCUTS[mode])
        yata.wait_for_view(mode)
        yata.wait(
            lambda: any(
                node.text == "todo"
                for node in yata.window.find_all(role="text", states={"editable"})
            ),
            "the filter query to survive the switch",
        )
        yata.wait(
            lambda: yata.matches() == ["todo.txt"],
            "the narrowed listing to survive the switch",
        )


def test_list_column_resize_tracks_the_pointer_without_an_initial_jump(yata):
    yata.switch_view("List")
    for label in ["Name", "Mode", "Size", "Type", "Modified"]:
        heading = yata.wait(
            lambda: yata.pane().find(role="button", name=label),
            f"the {label} heading to appear",
        )
        cell = heading.parent
        assert cell is not None
        before = cell.screen_bounds()
        start = (before.x + before.width - 3, before.y + before.height // 2)
        yata.pointer.drag_points(start, (start[0] - 12, start[1]))
        yata.wait(
            lambda: abs(cell.screen_bounds().width - (before.width - 12)) <= 2,
            f"the {label} column to shrink by the pointer's 12-pixel movement",
        )


def _has_check_mark(option) -> bool:
    """A chosen appearance option shows a trailing check image."""

    images = option.find_all(role="image")
    # The leading image is the option's own icon; a visible second image is the
    # check mark.
    return len(images) > 1
