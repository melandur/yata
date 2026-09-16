# SPDX-License-Identifier: MIT
"""Escape dismisses transient UI before clearing the active pane selection."""

import pytest

from harness.modes import ALL_MODES, NEXT_ENTRY_KEY

TRANSIENT_SURFACES = [
    "menu",
    "properties",
    "rename",
    "new-folder",
    "new-file",
    "location",
    "filter",
    "preview",
]
MODE_DEPENDENT_TRANSIENTS = {"new-folder", "preview", "rename"}


def _transient_dismiss_cases():
    cases = []
    for surface in TRANSIENT_SURFACES:
        modes = ALL_MODES if surface in MODE_DEPENDENT_TRANSIENTS else [
            mode for mode in ALL_MODES if mode.id == "columns"
        ]
        for mode in modes:
            cases.append(
                pytest.param(
                    mode.values[0],
                    surface,
                    marks=mode.marks,
                    id=f"{surface}-{mode.id}",
                )
            )
    return cases


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.preferences(single_click_previews=False)
def test_escape_clears_selection_without_navigation(yata, mode, multiple):
    root = yata.fixture.root.name
    if multiple:
        yata.select_entry("todo.txt", root)
        yata.click_entry_with("readme.md", ["ctrl"], root)
    else:
        yata.select_entry("readme.md", root)
    focused = "readme.md"
    yata.wait_for_selection(["readme.md", "todo.txt"] if multiple else [focused], root)
    panes = yata.pane_names()

    yata.keyboard.press("Escape")

    yata.wait_for_selection([], root)
    yata.wait_for_focused_entry(focused)
    assert yata.pane_names() == panes
    yata.keyboard.press(NEXT_ENTRY_KEY[mode])
    yata.wait_for_selection(["todo.txt"], root)
    yata.wait_for_focused_entry("todo.txt")


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.preferences(single_click_previews=False)
def test_enter_after_escape_opens_the_focused_folder(yata, mode):
    root = yata.fixture.root.name
    yata.select_entry_with_keyboard("documents")
    yata.wait_for_focused_entry("documents")
    yata.keyboard.press("Escape")
    yata.wait_for_selection([], root)
    yata.wait_for_focused_entry("documents")

    yata.keyboard.press("Return")

    yata.wait_for_directory("documents")
    yata.wait_for_entries(["notes.txt", "report.md", "spreadsheet.csv"], "documents")


@pytest.mark.preferences(browser_mode="columns", single_click_previews=False)
def test_escape_only_clears_the_active_column(yata):
    root = yata.fixture.root.name
    yata.open_directory("documents", directory=root)
    yata.select_entry("notes.txt", "documents")
    parent_selection = yata.selected_names(root)
    yata.keyboard.press("Escape")
    yata.wait_for_selection([], "documents")
    assert yata.selected_names(root) == parent_selection
    assert yata.pane_names() == [root, "documents"]
    yata.wait_for_focused_entry("notes.txt")


@pytest.mark.parametrize("mode,surface", _transient_dismiss_cases())
@pytest.mark.preferences(single_click_previews=False)
def test_escape_dismisses_transient_before_selection(yata, mode, surface):
    root = yata.fixture.root.name
    yata.select_entry("readme.md", root)
    if surface in ("menu", "properties"):
        yata.open_context_menu("readme.md", root)
        if surface == "properties":
            yata.choose_menu_item("Properties")
            yata.wait_for_dialog()
    elif surface == "new-file":
        yata.pointer.right_click(yata.pane(), at=yata.background_point())
        yata.choose_menu_item("New File")
        yata.editable_field()
    elif surface == "preview":
        yata.keyboard.press("space")
        yata.wait(yata.preview, "preview to open")
    else:
        shortcut = {"rename": "F2", "new-folder": "ctrl+shift+n", "location": "ctrl+l", "filter": "ctrl+f"}[surface]
        yata.keyboard.press(shortcut)
        yata.editable_field()

    yata.keyboard.press("Escape")

    if surface == "menu":
        yata.wait_for_menu_closed()
    elif surface == "properties":
        yata.wait(lambda: yata.dialog() is None, "properties to close")
    elif surface == "preview":
        yata.wait(lambda: yata.preview() is None, "preview to close")
    expected = {"new-folder": "new folder", "new-file": "new file"}.get(surface, "readme.md")
    yata.wait_for_selection([expected], root)
    if surface in ("new-folder", "new-file"):
        assert yata.fixture.path(expected).exists()
    yata.keyboard.press("Escape")
    yata.wait_for_selection([], root)
    expected_panes = [root, "new folder"] if mode == "Columns" and surface == "new-folder" else [root]
    assert yata.pane_names() == expected_panes


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("had_range", [False, True], ids=["no-range", "had-range"])
@pytest.mark.preferences(single_click_previews=False)
def test_shift_after_escape_starts_on_the_focused_entry(yata, mode, had_range):
    root = yata.fixture.root.name
    next_key = NEXT_ENTRY_KEY[mode]
    yata.wait_for_focused_entry("archive")
    yata.wait_for_selection(["archive"], root)
    if had_range:
        yata.keyboard.press(f"shift+{next_key}")
        yata.wait_for_selection(["archive", "documents"], root)
        yata.wait_for_focused_entry("documents")
        focused = "documents"
        first = ["documents"]
        second = ["documents", "pictures"]
    else:
        focused = "archive"
        first = ["archive"]
        second = ["archive", "documents"]

    yata.keyboard.press("Escape")
    yata.wait_for_selection([], root)
    yata.wait_for_focused_entry(focused)

    yata.keyboard.press(f"shift+{next_key}")
    yata.wait_for_selection(first, root)
    yata.wait_for_focused_entry(focused)

    yata.keyboard.press(f"shift+{next_key}")
    yata.wait_for_selection(second, root)
    yata.wait_for_focused_entry(second[-1])
