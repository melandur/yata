# SPDX-License-Identifier: MIT
"""Properties measures directory contents rather than directory metadata."""

import pytest


def _measurement_finished(dialog):
    spinner = dialog.find(name="Calculating folder size")
    return spinner is None or not spinner.is_rendered()


@pytest.fixture
def sized_folder(fixture_tree):
    fixture_tree.populate(
        {
            "sized-folder": {
                "top.txt": "abc",
                "nested": {"child.txt": "12345", ".hidden.txt": "1234567"},
                ".hidden": {"visible": {"file.txt": "123"}},
            }
        }
    )
    folder = fixture_tree.path("sized-folder")
    (folder / "nested/loop").symlink_to(folder, target_is_directory=True)
    (folder / "outside").symlink_to(fixture_tree.path("todo.txt"))
    return folder


@pytest.mark.parametrize("current_folder", [False, True], ids=["entry", "current-folder"])
def test_properties_calculates_nested_and_hidden_file_sizes(
    sized_folder, yata, current_folder
):
    if current_folder:
        yata.open_directory(sized_folder.name)
        yata.pointer.right_click(yata.pane(), at=yata.background_point())
        yata.wait(yata.context_menu, "the folder context menu")
    else:
        yata.open_context_menu(sized_folder.name)
    yata.choose_menu_item("Properties")
    dialog = yata.wait_for_dialog()

    yata.wait(
        lambda: dialog.find(role="label", name="18 B"),
        "Properties to show the recursive size without following symlinks",
    )
    yata.wait(lambda: _measurement_finished(dialog), "the size spinner to disappear")
    assert dialog.find(role="label", name="4 files, 1 folder")


def test_properties_explains_unreadable_folder_contents(sized_folder, yata):
    blocked = sized_folder / ".hidden"
    blocked.chmod(0)
    try:
        yata.open_context_menu(sized_folder.name)
        yata.choose_menu_item("Properties")
        dialog = yata.wait_for_dialog()
        yata.wait(lambda: _measurement_finished(dialog), "the measurement to finish")
        assert dialog.find(role="label", name="≥ 15 B")
        assert dialog.find(role="label", name="≥ 4 files, ≥ 1 folder")
        message = "Totals are incomplete.\nSome folders or entries couldn't be read."
        warning = yata.wait(lambda: dialog.find(name=message), "the incomplete measurement warning")
        assert warning.is_rendered()
        yata.pointer.move_to(*warning.screen_bounds().center)
        yata.wait(
            lambda: yata.application.application_node.find(role="label", name=message),
            "the warning tooltip",
        )
    finally:
        blocked.chmod(0o755)


@pytest.mark.parametrize("name, expected", [("archive", "0 B"), ("readme.md", "10 B")])
def test_properties_shows_zero_for_empty_folders_and_preserves_file_sizes(
    yata, name, expected
):
    yata.open_context_menu(name)
    yata.choose_menu_item("Properties")
    dialog = yata.wait_for_dialog()

    yata.wait(
        lambda: dialog.find(role="label", name=expected),
        f"Properties to show {expected}",
    )
    yata.wait(lambda: _measurement_finished(dialog), "no spinner after measurement")
