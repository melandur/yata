# SPDX-License-Identifier: MIT
"""Empty-space clicks clear selection without taking over item clicks or drags."""

import pytest

from harness.modes import ALL_MODES


def _select_files(yata):
    root = yata.fixture.root.name
    yata.select_entry("readme.md", root)
    yata.click_entry_with("todo.txt", ["ctrl"], root)
    yata.wait_for_selection(["readme.md", "todo.txt"], root)
    return root


def _blank_point(yata, directory):
    bounds = yata.pane(directory).screen_bounds()
    return bounds.center[0], bounds.y + bounds.height - 60


@pytest.mark.parametrize("mode", ALL_MODES)
def test_background_click_clears_all_selection(yata, mode):
    root = _select_files(yata)
    yata.pointer.click(yata.pane(root), at=_blank_point(yata, root))
    yata.wait(lambda: not yata.all_selected_names(), "empty space to deselect every file")
    assert yata.pane().name == root


@pytest.mark.parametrize("mode", ALL_MODES)
def test_background_press_does_not_clear_before_drag_intent(yata, mode):
    root = _select_files(yata)
    start = _blank_point(yata, root)
    end = yata.entry("todo.txt", root).screen_bounds().center

    def still_selected():
        assert yata.selected_names(root) == ["readme.md", "todo.txt"]

    yata.pointer.drag_points(start, end, after_press=still_selected)
    yata.wait(lambda: bool(yata.selected_names(root)), "marquee selection to survive release")


def test_clicking_an_empty_column_clears_other_columns_without_closing_them(yata):
    yata.open_directory("archive")
    _select_files(yata)
    panes = yata.pane_names()
    yata.pointer.click(yata.pane("archive"), at=_blank_point(yata, "archive"))
    yata.wait(lambda: not yata.all_selected_names(), "empty column to clear all selections")
    assert yata.pane_names() == panes
    assert yata.current_directory() == "archive"


def test_clicking_beside_the_last_column_clears_selection(yata):
    root = _select_files(yata)
    window = yata.window.screen_bounds()
    pane = yata.pane(root).screen_bounds()
    point = (window.x + window.width - 40, pane.center[1])
    yata.pointer.click(yata.window, at=point)
    yata.wait(lambda: not yata.all_selected_names(), "blank space beside Columns to deselect")
