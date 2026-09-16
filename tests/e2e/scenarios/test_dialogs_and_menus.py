# SPDX-License-Identifier: MIT
"""Context menus, dialogs, Escape handling, and invalid operations."""

from __future__ import annotations

import shlex
import shutil

import pytest

from harness.modes import ALL_MODES

ENTRY_MENU_ITEMS = {"Open", "Cut", "Copy", "Rename", "Move to Trash", "Properties"}


@pytest.fixture
def executable_file(fixture_tree):
    program = fixture_tree.path("run-me")
    shutil.copy2(shutil.which("true"), program)
    return program


@pytest.fixture
def observable_executable_file(fixture_tree):
    program = fixture_tree.path("run-me")
    marker = fixture_tree.path("run-me.executed")
    program.write_text(f"#!/bin/sh\nprintf executed > {shlex.quote(str(marker))}\n")
    program.chmod(0o755)
    return program


def test_the_entry_context_menu_offers_named_actions_and_accelerators(yata):
    yata.open_context_menu("todo.txt")

    menu = yata.context_menu()
    assert menu is not None, "the context menu should have the menu role"
    items = menu.find_all(role="menu item")
    assert items, "menu entries should have the menu item role"
    assert all(node.name for node in items), "every menu item needs a name"
    assert yata.menu_item("Copy").description == "Ctrl+C", (
        "the accelerator belongs in the description, not the name"
    )
    yata.dismiss_menu()


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("shortcut,activation", [("Menu", "Return"), ("shift+F10", "space")])
@pytest.mark.preferences(show_hidden=False, single_click_previews=False)
def test_keyboard_context_menu_targets_selection_and_owns_keys(yata, mode, shortcut, activation):
    root = yata.fixture.root.name
    before = yata.fixture.listing()
    yata.select_entry("todo.txt", root)
    yata.wait_for_focused_entry("todo.txt")
    yata.keyboard.press(shortcut)
    yata.wait(yata.context_menu, "the keyboard item menu")
    assert ENTRY_MENU_ITEMS <= set(yata.menu_items())
    assert "New Folder" not in yata.menu_items()

    yata.keyboard.press("Home")
    yata.wait(lambda: "focused" in yata.menu_item("Open").states, "Home to focus Open")
    yata.keyboard.press("Up")
    yata.wait(
        lambda: "focused" in yata.menu_item("Permanently delete").states,
        "Up to wrap to the last action",
    )
    yata.keyboard.press("Down")
    yata.wait(lambda: "focused" in yata.menu_item("Open").states, "Down to wrap to Open")
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.context_menu() is None, "Escape to dismiss the menu")
    yata.wait_for_selection(["todo.txt"], root)
    yata.wait_for_focused_entry("todo.txt")
    assert yata.fixture.listing() == before

    yata.click_entry_with("readme.md", ["ctrl"], directory=root)
    yata.wait_for_selection(["readme.md", "todo.txt"], root)
    yata.keyboard.press(shortcut)
    yata.wait(yata.context_menu, "the multi-selection menu")
    assert "Rename" not in yata.menu_items()
    yata.keyboard.press("ctrl+a")
    assert yata.context_menu() is not None
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.context_menu() is None, "the multi-selection menu to close")
    yata.wait_for_selection(["readme.md", "todo.txt"], root)

    yata.keyboard.press("Escape")
    yata.wait_for_selection([], root)
    yata.keyboard.press(shortcut)
    yata.wait(yata.context_menu, "the unselected pane menu")
    assert "New Folder" in yata.menu_items()
    yata.keyboard.press("Home")
    for _ in range(30):
        if "focused" in yata.menu_item("Select All").states:
            break
        yata.keyboard.press("Down")
    assert "focused" in yata.menu_item("Select All").states
    yata.keyboard.press(activation)
    yata.wait(lambda: yata.context_menu() is None, f"{activation} to activate Select All")
    yata.wait_for_selection([entry.name for entry in yata.entries(root)], root)


def test_the_pane_context_menu_offers_directory_actions(yata):
    yata.pointer.right_click(yata.pane(), at=yata.background_point())
    yata.wait(yata.context_menu, "the pane context menu")

    offered = set(yata.menu_items())
    assert {"New Folder", "Select All", "Refresh"} <= offered, (
        f"unexpected pane menu {sorted(offered)}"
    )
    yata.dismiss_menu()


def test_folder_background_customize_targets_the_presented_directory(yata):
    root = yata.fixture.root.name
    yata.pointer.right_click(yata.pane(root), at=yata.background_point(root))
    yata.wait(yata.context_menu, "the pane context menu")
    yata.choose_menu_item("Customize…")

    dialog = yata.wait_for_dialog()
    assert "Customize Folder" in dialog.dump()
    assert root in dialog.dump()
    yata.pointer.click(yata.dialog_button("Done"))
    yata.wait(lambda: yata.dialog() is None, "the customize dialog to close")


@pytest.mark.preferences(browser_mode="columns")
def test_folder_background_customize_targets_a_non_active_ancestor_column(yata):
    nested = yata.fixture.path("documents/nested")
    nested.mkdir()
    (nested / "child.txt").write_text("child")
    yata.open_directory("documents")
    yata.open_directory("nested", directory="documents")

    yata.pointer.right_click(
        yata.pane("documents"), at=yata.background_point("documents")
    )
    yata.wait(yata.context_menu, "the ancestor pane context menu")
    yata.choose_menu_item("Customize…")

    dialog = yata.wait_for_dialog()
    contents = dialog.dump()
    assert "Customize Folder" in contents
    assert "documents" in contents
    assert "nested" not in contents
    yata.pointer.click(yata.dialog_button("Done"))
    yata.wait(lambda: yata.dialog() is None, "the customize dialog to close")


def _open_properties(yata, name, directory=None):
    yata.open_context_menu(name, directory=directory)
    yata.choose_menu_item("Properties")
    return yata.wait_for_dialog()


def test_executable_without_handler_requires_confirmation(executable_file, yata):
    yata.double_click_entry(executable_file.name)

    dialog = yata.wait_for_dialog()
    assert "Run this program?" in dialog.dump()
    yata.wait(
        lambda: "focused" in yata.dialog_button("Cancel").states,
        "Cancel to receive initial focus",
    )
    assert yata.dialog_button("Close dialog").activate()
    yata.wait(lambda: yata.dialog() is None, "the close button to dismiss the dialog")

    yata.double_click_entry(executable_file.name)
    yata.pointer.click(yata.dialog_button("Run"))
    yata.wait(lambda: yata.dialog() is None, "the confirmed program to launch")


def test_executable_context_menu_offers_confirmed_run(observable_executable_file, yata):
    marker = observable_executable_file.with_name("run-me.executed")
    yata.open_context_menu(observable_executable_file.name)
    assert {"Open", "Open With…", "Run"} <= set(yata.menu_items())
    yata.choose_menu_item("Run")

    dialog = yata.wait_for_dialog()
    assert "Run this program?" in dialog.dump()
    yata.pointer.click(yata.dialog_button("Cancel"))
    yata.wait(lambda: yata.dialog() is None, "the cancelled run dialog to close")
    assert not marker.exists(), "Cancel must not launch the program"

    yata.open_context_menu(observable_executable_file.name)
    yata.choose_menu_item("Run")
    yata.pointer.click(yata.dialog_button("Run"))
    yata.wait(lambda: yata.dialog() is None, "the confirmed program to launch")
    yata.wait(marker.exists, "the confirmed program to create its marker")


def test_properties_pins_a_folder_and_offers_unpin_afterwards(yata):
    dialog = _open_properties(yata, "documents")
    pin = dialog.find(role="button", name="Pin")
    assert pin is not None, dialog.dump()
    assert "sensitive" in pin.states
    yata.pointer.click(pin)
    yata.wait(lambda: yata.dialog() is None, "the dialog to close after pinning")
    yata.wait(
        lambda: yata.window.find(role="button", name="documents"),
        "the pinned sidebar row",
    )

    dialog = _open_properties(yata, "documents")
    unpin = dialog.find(role="button", name="Unpin")
    assert unpin is not None, (
        f"Properties must offer Unpin for a pinned folder\n{dialog.dump()}"
    )
    assert "sensitive" in unpin.states, "the Unpin control must stay readable"
    assert dialog.find(role="button", name="Pin") is None

    yata.pointer.click(unpin)
    yata.wait(lambda: yata.dialog() is None, "the dialog to close after unpinning")
    yata.wait(
        lambda: yata.window.find(role="button", name="documents") is None,
        "the sidebar row to disappear",
    )


@pytest.mark.preferences(browser_mode="columns")
@pytest.mark.parametrize("opener,dismissal", [
    ("keyboard-menu", "Escape"),
    ("pointer-menu", "Close dialog"),
    ("shortcut", "backdrop"),
    ("pointer-menu", "Rename"),
])
def test_file_properties_describes_the_file_without_pin_actions_and_closes(
    yata, opener, dismissal,
):
    yata.fixture.path("documents/readme.md").write_text("Nested fixture\n")
    yata.open_directory("documents")
    yata.select_entry("readme.md", "documents")
    yata.wait_for_focused_entry("readme.md")
    if opener == "keyboard-menu":
        yata.keyboard.press("shift+F10")
        yata.wait(yata.context_menu, "the child-column item menu")
        yata.keyboard.press("Home")
        for _ in range(30):
            if yata.menu_item("Properties").has_state("focused"):
                break
            yata.keyboard.press("Down")
        assert yata.menu_item("Properties").has_state("focused")
        yata.keyboard.press("Return")
        dialog = yata.wait_for_dialog()
    elif opener == "shortcut":
        yata.keyboard.press("alt+Return")
        dialog = yata.wait_for_dialog()
    else:
        dialog = _open_properties(yata, "readme.md", "documents")
    assert "documents/readme.md" in dialog.dump(), "the dialog should describe the child file"
    assert dialog.find(role="button", name="Pin") is None, dialog.dump()
    assert dialog.find(role="button", name="Unpin") is None, dialog.dump()

    if dismissal == "Escape":
        yata.keyboard.press("Escape")
    elif dismissal == "backdrop":
        bounds = yata.window.screen_bounds()
        yata.pointer.click(yata.window, at=(bounds.x + 5, bounds.y + 5))
    else:
        yata.pointer.click(yata.dialog_button(dismissal))
    yata.wait(lambda: yata.dialog() is None, "Properties to close")
    if dismissal == "Rename":
        field = yata.editable_field()
        assert field.text == "readme.md", "Properties must hand focus to the rename editor"
        yata.keyboard.press("Escape")
    yata.wait_for_focused_entry("readme.md")
    yata.wait_for_selection(["readme.md"], "documents")
    yata.keyboard.press("Up")
    yata.wait_for_focused_entry("notes.txt")
    yata.wait_for_selection(["notes.txt"], "documents")
    assert yata.fixture.path("documents/readme.md").read_text() == "Nested fixture\n"
    assert yata.fixture.path("readme.md").read_text() == "# Fixture\n"


def test_renaming_onto_an_existing_name_is_rejected(yata):
    fixture = yata.fixture

    yata.select_entry("todo.txt")
    yata.keyboard.press("F2")
    yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("readme.md")
    yata.keyboard.press("Return")

    assert fixture.path("todo.txt").exists(), "the rename must not silently succeed"
    assert fixture.path("readme.md").read_text() == "# Fixture\n", (
        "the existing file must keep its contents"
    )
    yata.keyboard.press("Escape")


def test_the_shortcut_reference_opens_and_closes(yata):
    yata.keyboard.press("F1")

    yata.wait(
        lambda: yata.window.find(role="label", name="Keyboard shortcuts"),
        "the shortcut reference to open",
    )
    for chord in ["Ctrl+Alt+Space", "Ctrl+Alt+← / →", "Ctrl+Alt+↑ / ↓", "Ctrl+Alt+M"]:
        assert yata.window.find(role="label", name=chord, rendered=False) is not None
    yata.keyboard.press("Tab")
    yata.keyboard.press("End")
    description = yata.window.find(role="label", name="Seek −5 / +5 seconds", rendered=False)
    scroll = next(node for node in description.ancestors() if node.role == "scroll pane")
    scrollbar = scroll.find(role="scroll bar")
    bounds = description.window_bounds()
    assert bounds.x + bounds.width <= scrollbar.window_bounds().x

    yata.keyboard.press("Escape")
    yata.wait(
        lambda: yata.window.find(role="label", name="Keyboard shortcuts") is None,
        "Escape to close the shortcut reference",
    )


def compress_from_the_context_menu(yata, entry_name, archive_name):
    yata.open_context_menu(entry_name)
    yata.choose_menu_item("Compress…")
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text(archive_name)
    yata.wait(
        lambda: field.text == archive_name, f"{archive_name!r} to reach the name field"
    )
    return field


def test_an_invalid_archive_name_keeps_the_compress_dialog_open(yata):
    compress_from_the_context_menu(yata, "readme.md", "../escape")

    yata.keyboard.press("Return")

    dialog = yata.wait_for_dialog()
    assert dialog.name == "Compress 1 item", (
        f"an invalid name must keep the dialog open, got {dialog.name!r}"
    )
    assert not yata.fixture.path("escape.zip").exists(), (
        "an invalid name must not produce an archive"
    )
    yata.keyboard.press("Escape")


def test_enter_submits_compress_and_extract_to_dialogs(yata):
    compress_from_the_context_menu(yata, "readme.md", "bundle")
    yata.keyboard.press("Return")
    yata.wait(lambda: yata.dialog() is None, "the compress dialog to close")
    yata.wait(
        lambda: yata.fixture.path("bundle.zip").exists(), "the archive to be created"
    )

    destination = yata.fixture.path("unpacked")
    yata.open_context_menu("bundle.zip")
    yata.choose_menu_item("Extract to…")
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text(str(destination))
    yata.wait(
        lambda: field.text == str(destination), "the destination to reach the field"
    )

    yata.keyboard.press("Return")

    yata.wait(
        lambda: (destination / "readme.md").exists(),
        "Enter to extract into the destination",
    )
    assert (destination / "readme.md").read_text() == "# Fixture\n"


def test_enter_submits_the_copy_to_dialog(yata):
    destination = yata.fixture.path("documents")

    yata.open_context_menu("todo.txt")
    yata.choose_menu_item("Copy to…")
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text(str(destination))
    yata.wait(
        lambda: field.text == str(destination), "the destination to reach the field"
    )

    yata.keyboard.press("Return")

    yata.wait(
        lambda: (destination / "todo.txt").exists(),
        "Enter to copy into the destination",
    )
