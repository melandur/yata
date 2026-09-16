# SPDX-License-Identifier: MIT

import tarfile
import zipfile

import pytest

from harness.modes import ALL_MODES


@pytest.fixture
def fixture_tree(fixture_tree, request):
    extension = request.node.callspec.params.get("extension", "zip")
    fixture_tree.path(f"archive.{extension}").write_bytes(b"original archive")
    fixture_tree.path(f"archive (1).{extension}").write_bytes(b"previous archive")
    return fixture_tree


def request_archive_collision(yata, format="ZIP"):
    yata.select_entry("todo.txt")
    yata.open_context_menu("todo.txt")
    yata.choose_menu_item("Compress…")
    dialog = yata.wait_for_dialog()
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("archive")
    yata.wait(lambda: field.text == "archive", "archive name input")
    yata.pointer.click(dialog.find(role="toggle button", name=format))
    yata.pointer.click(yata.dialog_button("Compress"))
    yata.wait(
        lambda: (dialog := yata.dialog()) is not None and dialog.name == "File already exists",
        "archive collision prompt",
    )


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("format,extension", [("ZIP", "zip"), ("TAR.GZ", "tar.gz")])
@pytest.mark.parametrize("activation", ["pointer", "Return"])
def test_keep_both_preserves_archives_and_selects_each_numbered_output(yata, mode, format, extension, activation):
    fixture = yata.fixture
    original = fixture.path(f"archive.{extension}")
    previous = fixture.path(f"archive (1).{extension}")
    for suffix in [2, 3]:
        request_archive_collision(yata, format)
        if activation == "pointer":
            yata.pointer.click(yata.dialog_button("Keep Both"))
        else:
            yata.wait(lambda: yata.dialog_button("Replace").has_state("focused"), "initial Replace focus")
            yata.keyboard.press("shift+Tab")
            yata.wait(lambda: yata.dialog_button("Keep Both").has_state("focused"), "Keep Both focus")
            yata.keyboard.press("Return")
        name = f"archive ({suffix}).{extension}"
        path = fixture.path(name)
        yata.wait(path.exists, "numbered archive publication")
        yata.wait(lambda: yata.dialog() is None, "archive progress dismissal")
        yata.wait_for_selection([name])
        yata.wait(lambda: yata.on_screen(yata.entry(name)), "numbered archive reveal")
        if format == "ZIP":
            with zipfile.ZipFile(path) as archive:
                assert archive.namelist() == ["todo.txt"]
                assert archive.read("todo.txt") == fixture.path("todo.txt").read_bytes()
        else:
            with tarfile.open(path, "r:gz") as archive:
                assert archive.getnames() == ["todo.txt"]
                assert archive.extractfile("todo.txt").read() == fixture.path("todo.txt").read_bytes()
        assert original.read_bytes() == b"original archive"
        assert previous.read_bytes() == b"previous archive"


@pytest.mark.parametrize("choice", ["Cancel", "Escape", "Replace"])
def test_archive_conflict_keyboard_choices_preserve_cancel_and_replace_behavior(yata, choice):
    original = yata.fixture.path("archive.zip")
    request_archive_collision(yata)
    yata.wait(lambda: yata.dialog_button("Replace").has_state("focused"), "initial Replace focus")
    if choice == "Escape":
        yata.keyboard.press("Escape")
    else:
        if choice == "Cancel":
            yata.keyboard.press("shift+Tab")
            yata.keyboard.press("shift+Tab")
            yata.wait(lambda: yata.dialog_button("Cancel").has_state("focused"), "Cancel focus")
        yata.keyboard.press("Return")
    yata.wait(lambda: yata.dialog() is None, "conflict dismissal")
    assert yata.fixture.path("archive (1).zip").read_bytes() == b"previous archive"
    assert not yata.fixture.path("archive (2).zip").exists()
    if choice == "Replace":
        with zipfile.ZipFile(original) as archive:
            assert archive.namelist() == ["todo.txt"]
            assert archive.read("todo.txt") == yata.fixture.path("todo.txt").read_bytes()
    else:
        assert original.read_bytes() == b"original archive"
