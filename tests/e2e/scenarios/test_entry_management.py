# SPDX-License-Identifier: MIT
"""Creating, renaming, trashing, deleting, and undoing."""

from __future__ import annotations

import pytest

from harness.modes import ALL_MODES, COLUMNS_AND_ONE


def start_new_file(yata, select=True):
    if select:
        yata.select_entry("readme.md")
    yata.pointer.right_click(yata.pane(), at=yata.background_point())
    yata.choose_menu_item("New File")
    field = yata.editable_field()
    yata.wait(lambda: field.text.startswith("new file"), "the created file's editor")
    return field


@pytest.mark.parametrize("mode", ALL_MODES)
def test_invalid_new_file_names_can_be_corrected(yata, mode):
    name = "bad/name"
    field = start_new_file(yata)
    original = yata.fixture.names()
    yata.keyboard.type_text(name)
    yata.wait(lambda: field.text == name, "the invalid name to appear")
    yata.keyboard.press("Return")
    yata.wait(lambda: yata.window.find(role="text", name="Rename", states={"editable"}) is None, "the invalid edit to close")
    assert yata.fixture.names() == original
    yata.select_entry_with_keyboard("new file")
    yata.keyboard.press("F2")
    yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("corrected")
    yata.keyboard.press("Return")
    yata.wait(lambda: yata.fixture.path("corrected").is_file(), "the corrected file on disk")
    yata.entry("corrected")


@pytest.mark.parametrize("kind", ["file", "folder"])
def test_clicking_inside_keeps_the_new_entry_and_preserves_its_name(yata, kind):
    name = " padded "
    if kind == "folder":
        yata.select_entry("readme.md")
        yata.keyboard.press("ctrl+shift+n")
        field = yata.editable_field()
    else:
        field = start_new_file(yata)
    yata.keyboard.type_text(name)
    yata.wait(lambda: field.text == name, "the name to appear")
    yata.pointer.click(field)
    yata.keyboard.press("Return")
    yata.wait(lambda: yata.fixture.path(name).exists(), "the exact name on disk")
    assert yata.fixture.path(name).is_dir() == (kind == "folder")
    yata.wait(
        lambda: yata.window.find(role="text", states={"editable"}) is None,
        "the submitted prompt to close",
    )


@pytest.mark.parametrize("kind,name", [("file", "todo.txt"), ("folder", "archive")])
def test_creating_an_existing_name_does_not_overwrite(yata, kind, name):
    yata.select_entry("readme.md")
    if kind == "folder":
        yata.keyboard.press("ctrl+shift+n")
    else:
        yata.pointer.right_click(yata.pane(), at=yata.background_point())
        yata.choose_menu_item("New File")
    field = yata.editable_field()
    original = yata.fixture.listing()
    yata.keyboard.type_text(name)
    yata.wait(lambda: field.text == name, "the existing name to appear")
    yata.keyboard.press("Return")
    dialog = yata.wait_for_dialog()
    assert dialog.name == "Unable to rename item"
    yata.pointer.click(yata.dialog_button("Close"))
    yata.wait(lambda: yata.dialog() is None, "the error to be dismissible")
    assert yata.fixture.listing() == original
    assert yata.fixture.path("todo.txt").read_text() == "todo\n"
    root = yata.fixture.root.name
    yata.select_entry("readme.md", root)
    yata.wait_for_selection(["readme.md"], root)
    if kind == "folder":
        assert yata.pane_names() == [root, "new folder"]


@pytest.mark.parametrize("kind", ["file", "folder"])
def test_new_items_can_be_created_in_an_initially_empty_directory(yata, kind):
    yata.open_directory("archive")
    if kind == "folder":
        yata.keyboard.press("ctrl+shift+n")
        yata.editable_field()
    else:
        start_new_file(yata, select=False)
    yata.keyboard.type_text("discarded")
    yata.keyboard.press("Escape")
    yata.entry("new " + kind, directory="archive")
    if kind == "folder":
        yata.keyboard.press("ctrl+shift+n")
        field = yata.editable_field()
    else:
        field = start_new_file(yata, select=False)
    yata.keyboard.type_text("kept")
    yata.wait(lambda: field.text == "kept", "the replacement name to appear")
    yata.keyboard.press("Return")
    yata.wait(lambda: yata.fixture.path("archive/kept").exists(), "the renamed item on disk")
    assert yata.fixture.path("archive/kept").is_dir() == (kind == "folder")
    yata.entry("kept", directory="archive")
    assert not yata.fixture.path("archive/discarded").exists()
    assert "Gtk-CRITICAL" not in yata.application.log()


@pytest.mark.parametrize("shortcut", ["F2", "ctrl+r"])
def test_rename_shortcuts(yata, shortcut):
    fixture = yata.fixture

    yata.select_entry("todo.txt")
    yata.keyboard.press(shortcut)
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("renamed.txt")
    yata.wait(lambda: field.text == "renamed.txt", "the new name to be typed")
    yata.keyboard.press("ctrl+r")
    assert yata.editable_field().text == "renamed.txt"
    yata.keyboard.press("Return")

    yata.wait(
        lambda: fixture.path("renamed.txt").exists(),
        "the file to be renamed on disk",
    )
    assert not fixture.path("todo.txt").exists()
    assert fixture.path("renamed.txt").read_text() == "todo\n"
    yata.entry("renamed.txt")


@pytest.mark.parametrize("shortcut", ["F2", "ctrl+r"])
def test_rename_shortcuts_leave_location_editing_alone(yata, shortcut):
    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+l")
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text(str(yata.fixture.path("documents")))
    yata.wait(lambda: field.text.endswith("documents"), "the location to be typed")
    yata.keyboard.press(shortcut)
    assert yata.editable_field().text == str(yata.fixture.path("documents"))
    yata.keyboard.press("Return")
    yata.wait_for_directory("documents")
    assert yata.fixture.path("todo.txt").exists()


def test_rename_from_the_context_menu(yata):
    fixture = yata.fixture

    yata.open_context_menu("readme.md")
    yata.choose_menu_item("Rename")
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("guide.md")
    yata.wait(lambda: field.text == "guide.md", "the new name to be typed")
    yata.keyboard.press("Return")

    yata.wait(lambda: fixture.path("guide.md").exists(), "the rename to apply")
    assert not fixture.path("readme.md").exists()


def test_delete_moves_the_entry_to_trash(yata):
    fixture = yata.fixture

    yata.select_entry("todo.txt")
    yata.keyboard.press("Delete")

    yata.wait(
        lambda: not fixture.path("todo.txt").exists(),
        "the file to leave the fixture tree",
    )
    yata.wait_for_entry_gone("todo.txt")
    trashed = yata.environment.trash_files
    assert trashed.exists() and any(trashed.iterdir()), (
        "the file should be recoverable from the isolated trash directory"
    )


@pytest.mark.parametrize("mode", COLUMNS_AND_ONE)
def test_permanent_delete_requires_confirmation_and_can_be_cancelled(yata, mode):
    fixture = yata.fixture
    assert yata.view_mode() == mode

    yata.select_entry("todo.txt")
    yata.keyboard.press("shift+Delete")

    dialog = yata.wait_for_dialog()
    assert dialog.role in ("dialog", "alert")
    assert dialog.name == "Permanently delete 1 item?", (
        f"unexpected dialog {dialog.name!r}"
    )
    assert fixture.path("todo.txt").exists(), (
        "nothing may be deleted before the confirmation is answered"
    )

    yata.pointer.click(yata.dialog_button("Cancel"))
    yata.wait(lambda: yata.dialog() is None, "the dialog to close")
    assert fixture.path("todo.txt").exists(), "cancelling must keep the file"

    yata.select_entry("todo.txt")
    yata.keyboard.press("shift+Delete")
    yata.wait_for_dialog()
    yata.pointer.click(yata.dialog_button("Permanently delete 1 item"))

    yata.wait(
        lambda: not fixture.path("todo.txt").exists(),
        "the file to be deleted",
    )
    yata.wait_for_entry_gone("todo.txt")
    trashed = yata.environment.trash_files
    assert not trashed.exists() or not any(trashed.iterdir()), (
        "a permanent delete must not go through the trash"
    )


@pytest.mark.parametrize("mode", COLUMNS_AND_ONE)
def test_permanent_delete_through_a_symlinked_parent(yata, mode):
    fixture = yata.fixture
    alias = fixture.path("documents-alias")
    alias.symlink_to(fixture.path("documents"), target_is_directory=True)

    yata.open_directory("documents-alias")
    yata.wait_for_directory("documents-alias")

    yata.select_entry("notes.txt", directory="documents-alias")
    yata.keyboard.press("shift+Delete")
    yata.wait_for_dialog()
    yata.pointer.click(yata.dialog_button("Permanently delete 1 item"))

    yata.wait(
        lambda: not fixture.path("documents/notes.txt").exists()
        or (yata.dialog() is not None and yata.dialog().name == "Completed with errors"),
        "the delete operation to finish",
    )
    assert not fixture.path("documents/notes.txt").exists()
    yata.wait_for_entry_gone("notes.txt", directory="documents-alias")
    yata.wait(lambda: yata.dialog() is None, "the confirmation dialog to close")
    assert alias.is_symlink()
    assert fixture.path("documents").is_dir()


def test_undo_restores_a_completed_move(yata):
    fixture = yata.fixture

    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+x")
    yata.open_directory("archive")
    yata.paste_into("archive")
    yata.wait(
        lambda: fixture.path("archive/todo.txt").exists(),
        "the move to complete",
    )

    yata.keyboard.press("ctrl+z")

    yata.wait(
        lambda: fixture.path("todo.txt").exists(),
        "undo to put the file back",
    )
    assert not fixture.path("archive/todo.txt").exists()
