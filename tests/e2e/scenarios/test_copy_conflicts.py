# SPDX-License-Identifier: MIT

import pytest


@pytest.mark.parametrize("activation", ["pointer", "Return"])
def test_keep_both_selects_the_numbered_copy_and_undo_preserves_originals(yata, activation):
    fixture = yata.fixture
    fixture.path("archive/todo.txt").write_text("existing\n")
    fixture.path("archive/todo (1).txt").write_text("previous copy\n")
    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+c")
    yata.open_directory("archive")
    yata.paste_into("archive")
    yata.wait_for_dialog()

    if activation == "pointer":
        yata.pointer.click(yata.dialog_button("Keep Both"))
    else:
        yata.wait(
            lambda: yata.dialog_button("Replace").has_state("focused"),
            "Replace to receive initial focus",
        )
        yata.keyboard.press("shift+Tab")
        yata.wait(
            lambda: yata.dialog_button("Keep Both").has_state("focused"),
            "Keep Both to receive keyboard focus",
        )
        yata.keyboard.press("Return")

    yata.wait(lambda: fixture.path("archive/todo (2).txt").exists(), "the numbered copy")
    yata.wait(
        lambda: yata.selected_names("archive") == ["todo (2).txt"],
        "the numbered copy to be selected",
    )
    assert fixture.path("archive/todo (2).txt").read_text() == "todo\n"
    # The copy can finish while the dismissing modal still owns keyboard input.
    yata.wait(lambda: yata.dialog() is None, "the conflict dialog to finish dismissing")
    yata.wait_for_focused_entry("todo (2).txt")
    yata.keyboard.press("ctrl+z")
    yata.wait(lambda: not fixture.path("archive/todo (2).txt").exists(), "copy undo")
    assert fixture.path("todo.txt").read_text() == "todo\n"
    assert fixture.path("archive/todo.txt").read_text() == "existing\n"
    assert fixture.path("archive/todo (1).txt").read_text() == "previous copy\n"


@pytest.mark.parametrize(
    "moving,action",
    [
        (False, "Cancel"),
        (False, "Escape"),
        (False, "Close dialog"),
        (True, "Cancel"),
    ],
    ids=["copy-Cancel", "copy-Escape", "copy-Close", "move-Cancel"],
)
def test_dismissing_a_copy_or_move_conflict_preserves_both_files(yata, moving, action):
    fixture = yata.fixture
    fixture.path("archive/todo.txt").write_text("existing\n")
    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+x" if moving else "ctrl+c")
    yata.open_directory("archive")
    yata.paste_into("archive")
    dialog = yata.wait_for_dialog()
    assert (dialog.find(role="button", name="Keep Both") is not None) == (not moving)

    if action == "Escape":
        yata.keyboard.press("Escape")
    else:
        yata.pointer.click(yata.dialog_button(action))
    yata.wait(lambda: yata.dialog() is None, "the conflict dialog to close")
    assert fixture.path("todo.txt").read_text() == "todo\n"
    assert fixture.path("archive/todo.txt").read_text() == "existing\n"
    assert not fixture.path("archive/todo (1).txt").exists()


def test_keep_both_applies_to_all_collisions_in_a_mixed_paste(yata):
    fixture = yata.fixture
    for name in ["notes.txt", "report.md"]:
        fixture.path(f"archive/{name}").write_text(f"existing {name}\n")
    yata.open_directory("documents")
    yata.select_entry_with_keyboard("notes.txt")
    yata.keyboard.press("ctrl+a")
    yata.keyboard.press("ctrl+c")
    yata.keyboard.press("alt+Up")
    yata.wait_for_directory(fixture.root.name)
    yata.open_directory("archive")
    yata.paste_into("archive")
    dialog = yata.wait_for_dialog()
    apply_all = dialog.find(name="Apply to All")
    assert apply_all is not None, dialog.dump()
    yata.pointer.click(apply_all)
    yata.pointer.click(yata.dialog_button("Keep Both"))
    yata.wait(
        lambda: all(
            fixture.path(f"archive/{name}").exists()
            for name in ["notes (1).txt", "report (1).md", "spreadsheet.csv"]
        ),
        "all mixed-paste copies",
    )
    for name, copied in [
        ("notes.txt", "notes (1).txt"),
        ("report.md", "report (1).md"),
        ("spreadsheet.csv", "spreadsheet.csv"),
    ]:
        assert fixture.path(f"archive/{copied}").read_bytes() == fixture.path(
            f"documents/{name}"
        ).read_bytes()
    for name in ["notes.txt", "report.md"]:
        assert fixture.path(f"archive/{name}").read_text() == f"existing {name}\n"
