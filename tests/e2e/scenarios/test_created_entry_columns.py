# SPDX-License-Identifier: MIT
"""Creation keeps the Miller path, selection, and real keyboard focus consistent."""

import pytest


def create_in_parent(yata, kind, stale_child):
    root = yata.fixture.root.name
    if stale_child:
        yata.open_directory("documents")
    yata.pointer.right_click(yata.pane(root), at=yata.background_point(root))
    yata.choose_menu_item("New Folder" if kind == "folder" else "New File")
    field = yata.wait(
        lambda: yata.window.find(role="text", name="Rename", states={"editable", "focused"}),
        "the parent rename editor to take keyboard focus",
    )
    original = "new " + kind
    yata.wait(lambda: field.text == original, "the default name")
    path = yata.fixture.path(original)
    assert path.is_dir() if kind == "folder" else path.is_file()
    yata.wait_for_selection([original], root)
    expected = [root, original] if kind == "folder" else [root]
    yata.wait(lambda: yata.pane_names() == expected, "the child path to follow creation")
    assert yata.current_directory() == root
    return field, original


@pytest.mark.preferences(browser_mode="columns", single_click_previews=False)
def test_created_folder_editor_stays_visible_in_a_narrow_window(yata):
    yata.select_entry("readme.md")
    bounds = yata.window.window_bounds()
    yata.keyboard.connection.resize_surface(bounds.width, bounds.height, 420, 300)
    yata.wait(lambda: yata.window.window_bounds().width == 420, "a narrow window")
    yata.keyboard.press("ctrl+shift+n")
    field = yata.wait(
        lambda: yata.window.find(role="text", name="Rename", states={"editable", "focused"}),
        "the new folder editor to remain visible in the parent",
    )
    yata.keyboard.type_text("visible-folder")
    yata.wait(lambda: field.text == "visible-folder", "typing in the visible editor")
    editor = field.window_bounds()
    root = yata.pane(yata.fixture.root.name).window_bounds()
    assert editor.width > 1 and editor.x >= max(root.x, 0)
    assert editor.x + editor.width <= yata.window.window_bounds().width
    yata.keyboard.press("Return")
    yata.wait(yata.fixture.path("visible-folder").is_dir, "the visible folder rename")


@pytest.mark.preferences(browser_mode="columns", single_click_previews=False)
@pytest.mark.parametrize("kind", ["file", "folder"])
@pytest.mark.parametrize("stale_child", [False, True], ids=["no-child", "stale-child"])
@pytest.mark.parametrize("completion", ["enter", "sibling", "navigate"])
def test_created_entry_completion_preserves_the_users_focus(yata, kind, stale_child, completion):
    root = yata.fixture.root.name
    field, original = create_in_parent(yata, kind, stale_child)
    yata.keyboard.type_text("renamed")
    yata.wait(lambda: field.text == "renamed", "typing to replace the entire default name")
    if completion == "enter":
        yata.keyboard.press("Return")
    elif completion == "sibling":
        yata.pointer.click(yata.entry("readme.md", root))
    else:
        yata.pointer.click(yata.sidebar_button("Home"))
    yata.wait(yata.fixture.path("renamed").exists, "the rename on disk")
    yata.wait(
        lambda: yata.window.find(role="text", name="Rename", states={"editable"}) is None,
        "the editor to close",
    )
    assert not yata.fixture.path(original).exists()
    if completion == "navigate":
        yata.wait_for_directory(yata.environment.home.name)
        assert root not in yata.pane_names()
    else:
        expected = [root, "renamed"] if kind == "folder" else [root]
        yata.wait(lambda: yata.pane_names() == expected, "the renamed child header")
        selected = "renamed" if completion == "enter" else "readme.md"
        yata.wait_for_selection([selected], root)
        yata.wait_for_directory(root)
        # No pointer correction: F2 must use the item selected by the previous action.
        yata.keyboard.press("F2")
        reopened = yata.wait(
            lambda: yata.window.find(role="text", name="Rename", states={"editable", "focused"}),
            "F2 to rename the still-selected parent item",
        )
        assert reopened.text == selected
        yata.keyboard.press("Escape")
    assert yata.window.find(role="dialog") is None
    assert "Gtk-CRITICAL" not in yata.application.log()
