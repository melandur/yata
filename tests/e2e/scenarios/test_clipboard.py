# SPDX-License-Identifier: MIT
"""Copy, cut, and paste through both the keyboard and the context menu."""

from __future__ import annotations

import pytest

from harness.modes import ALL_MODES, SINGLE_PANE_MODES


@pytest.mark.parametrize(
    "source, duplicate",
    [
        ("todo.txt", "todo (1).txt"),
        ("documents", "documents (1)"),
    ],
)
def test_same_folder_copy_creates_a_numbered_duplicate(yata, source, duplicate):
    fixture = yata.fixture
    yata.select_entry_with_keyboard(source)
    yata.keyboard.press("ctrl+d")
    yata.wait(lambda: fixture.path(duplicate).exists(), "the numbered copy")
    yata.entry(duplicate, directory=fixture.root.name)
    assert fixture.path(source).exists()
    if source == "documents":
        copied_file = fixture.path(f"{duplicate}/notes.txt")
        expected = fixture.path("documents/notes.txt").read_bytes()
    else:
        copied_file = fixture.path(duplicate)
        expected = b"todo\n"
    yata.wait(
        lambda: copied_file.is_file() and copied_file.read_bytes() == expected,
        "the numbered copy's contents to finish copying",
    )


@pytest.mark.parametrize("mode", ALL_MODES)
def test_copy_leaves_the_source_in_place(yata, mode):
    assert yata.view_mode() == mode
    fixture = yata.fixture

    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+c")
    yata.open_directory("archive")
    yata.paste_into("archive")

    yata.wait(
        lambda: (fixture.path("archive/todo.txt")).exists(),
        "the copy to land in archive",
    )
    assert fixture.path("todo.txt").exists(), "copying must not remove the source"
    assert fixture.path("archive/todo.txt").read_text() == "todo\n"
    yata.entry("todo.txt", directory="archive")


@pytest.mark.parametrize("mode", ALL_MODES)
def test_paste_targets_a_single_selected_directory(yata, mode):
    fixture = yata.fixture

    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+c")
    yata.select_entry_with_keyboard("archive")
    yata.keyboard.press("ctrl+v")

    yata.wait(
        lambda: fixture.path("archive/todo.txt").exists(),
        "the copy to land in the selected folder",
    )
    assert fixture.path("todo.txt").exists()


@pytest.mark.parametrize("mode", ALL_MODES)
def test_paste_into_parent_uses_the_current_directory(yata, mode):
    fixture = yata.fixture
    root = fixture.root.name

    yata.open_directory("documents")
    yata.select_entry("notes.txt")
    yata.keyboard.press("ctrl+c")
    yata.keyboard.press("alt+Up")
    yata.wait_for_directory(root)
    if mode != "Columns":
        yata.wait_for_selection(["documents" if mode == "List" else "archive"])
    yata.keyboard.press("ctrl+v")

    yata.wait(
        lambda: fixture.path("notes.txt").exists(),
        "the copy to land in the parent directory",
    )
    assert not fixture.path("archive/notes.txt").exists(), (
        "the auto-selected first folder must not steal the paste"
    )
    assert not fixture.path("documents/notes (1).txt").exists(), (
        "the restored selection must not steal the paste"
    )
    assert fixture.path("documents/notes.txt").exists()


@pytest.mark.parametrize("mode", SINGLE_PANE_MODES)
@pytest.mark.parametrize("selection", ["click", "Home"])
def test_paste_into_explicit_selection_after_returning_to_parent(yata, mode, selection):
    fixture = yata.fixture
    yata.open_directory("documents")
    yata.select_entry("notes.txt")
    yata.keyboard.press("ctrl+c")
    yata.keyboard.press("alt+Up")
    yata.wait_for_directory(fixture.root.name)
    restored = "documents" if mode == "List" else "archive"
    yata.wait_for_selection([restored])
    if selection == "click":
        yata.click_entry(restored)
    else:
        yata.keyboard.press(selection)
    destination = (
        "documents/notes (1).txt"
        if mode == "List" and selection == "click"
        else "archive/notes.txt"
    )
    yata.keyboard.press("ctrl+v")
    yata.wait(
        lambda: fixture.path(destination).exists(),
        "the copy to land in the explicitly selected folder",
    )
    assert not fixture.path("notes.txt").exists()


def test_opening_a_child_keeps_paste_under_the_pointer(yata):
    fixture = yata.fixture

    yata.open_directory("documents")
    yata.select_entry("notes.txt", directory="documents")
    yata.keyboard.press("ctrl+c")
    yata.keyboard.press("alt+Up")
    yata.wait_for_directory(fixture.root.name)
    yata.open_directory("archive")
    yata.keyboard.press("ctrl+v")

    yata.wait(
        lambda: fixture.path("notes.txt").exists(),
        "the copy to land in the parent column still under the pointer",
    )
    assert not fixture.path("archive/notes.txt").exists()


@pytest.mark.parametrize("mode", ALL_MODES)
def test_cut_moves_only_after_paste(yata, mode):
    fixture = yata.fixture

    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+x")

    assert fixture.path("todo.txt").exists(), (
        "cut must not touch the filesystem before the paste"
    )

    yata.open_directory("archive")
    yata.paste_into("archive")

    yata.wait(
        lambda: fixture.path("archive/todo.txt").exists(),
        "the cut file to arrive in archive",
    )
    yata.wait(
        lambda: not fixture.path("todo.txt").exists(),
        "the cut file to leave its source directory",
    )


@pytest.mark.parametrize("mode", ALL_MODES)
def test_context_menu_copy_and_paste(yata, mode):
    fixture = yata.fixture

    yata.open_context_menu("readme.md")
    assert "Copy" in yata.menu_items()
    yata.choose_menu_item("Copy")

    yata.open_directory("archive")
    _paste_from_context_menu(yata)

    yata.wait(
        lambda: fixture.path("archive/readme.md").exists(),
        "the context-menu copy to land in archive",
    )
    assert fixture.path("readme.md").exists()


@pytest.mark.parametrize("mode", ALL_MODES)
def test_context_menu_cut_and_paste(yata, mode):
    fixture = yata.fixture

    yata.open_context_menu("readme.md")
    yata.choose_menu_item("Cut")
    yata.open_directory("archive")
    _paste_from_context_menu(yata)

    yata.wait(
        lambda: fixture.path("archive/readme.md").exists()
        and not fixture.path("readme.md").exists(),
        "the context-menu cut to complete",
    )


def _paste_from_context_menu(yata):
    yata.pointer.right_click(yata.pane("archive"), at=yata.background_point("archive"))
    yata.wait(yata.context_menu, "the destination context menu")
    yata.choose_menu_item("Paste")


def test_skipping_one_collision_still_pastes_the_rest(yata):
    fixture = yata.fixture
    fixture.path("archive/notes.txt").write_text("existing\n")
    yata.open_directory("documents")
    yata.select_entry_with_keyboard("notes.txt")
    yata.keyboard.press("ctrl+a")
    yata.keyboard.press("ctrl+c")
    yata.keyboard.press("alt+Up")
    yata.wait_for_directory(fixture.root.name)
    yata.open_directory("archive")
    yata.paste_into("archive")

    dialog = yata.wait_for_dialog()
    assert dialog.name == "File already exists", (
        "a duplicate name must be surfaced rather than silently resolved"
    )
    assert dialog.find(role="button", name="Skip") is not None, (
        "skip must stay available when other items are already accepted"
    )
    assert dialog.find(name="Apply to All") is None, (
        "apply to all has no further conflicts left to apply to"
    )

    yata.pointer.click(yata.dialog_button("Skip"))
    yata.wait(lambda: yata.dialog() is None, "the conflict dialog to close")
    assert fixture.path("archive/notes.txt").read_text() == "existing\n", (
        "skipping must leave the conflicting file alone"
    )
    assert not fixture.path("archive/notes (1).txt").exists(), (
        "skipping must not create a numbered copy"
    )
    for name in ("report.md", "spreadsheet.csv"):
        source = fixture.path(f"documents/{name}")
        copied = fixture.path(f"archive/{name}")
        yata.wait(
            lambda: copied.is_file() and copied.read_bytes() == source.read_bytes(),
            f"the non-conflicting {name} copy to finish",
        )


def test_replacing_on_a_duplicate_name_overwrites(yata):
    fixture = yata.fixture
    fixture.path("archive/todo.txt").write_text("existing\n")

    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+c")
    yata.open_directory("archive")
    yata.paste_into("archive")

    yata.wait_for_dialog()
    yata.pointer.click(yata.dialog_button("Replace"))

    yata.wait(
        lambda: fixture.path("archive/todo.txt").read_text() == "todo\n",
        "the replaced file to take the pasted contents",
    )
    assert fixture.path("todo.txt").exists(), "the copy source must survive"


def test_paste_availability_follows_the_clipboard(yata):
    def paste_is_enabled() -> bool:
        yata.pointer.right_click(yata.pane(), at=yata.background_point())
        yata.wait(yata.context_menu, "the pane context menu")
        enabled = yata.menu_item("Paste").has_state("sensitive")
        yata.dismiss_menu()
        return enabled

    assert not paste_is_enabled(), (
        "Paste should be offered but disabled while the clipboard is empty"
    )

    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+c")

    assert paste_is_enabled(), "copying should enable Paste"


def test_copying_a_directory_copies_its_contents(yata):
    fixture = yata.fixture

    # Through the context menu: in Columns a plain click on a folder opens it.
    yata.open_context_menu("documents")
    yata.choose_menu_item("Copy")
    yata.open_directory("archive")
    yata.paste_into("archive")

    yata.wait(
        lambda: fixture.path("archive/documents/notes.txt").exists(),
        "the directory copy to include its contents",
    )
    assert sorted(fixture.names("archive/documents")) == [
        "notes.txt",
        "report.md",
        "spreadsheet.csv",
    ]
    assert fixture.path("documents/notes.txt").exists()
