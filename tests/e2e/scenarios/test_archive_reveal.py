# SPDX-License-Identifier: GPL-3.0-or-later
"""After compression completes, the new archive is selected and scrolled into view."""

import pytest

from harness import tree
from harness.fixtures import FixtureTree
from harness.modes import ALL_MODES


@pytest.fixture
def fixture_tree():
    files = {f"{index:03}.txt": f"{index}\n" for index in range(200)}
    fixture = FixtureTree.create(
        {"nested": files, "a": {"b": {"c": {"d": files}}}, **files}
    )
    try:
        yield fixture
    finally:
        fixture.cleanup()


def _compress(yata, entry_name, archive_name, directory, folder=""):
    for _ in range(3):
        yata.open_context_menu(entry_name, directory=directory)
        # Coordinate-free activation: the popover can still be settling when
        # the item is found, and a synthetic click then lands outside it.
        yata.menu_item("Compress…").activate()
        yata.wait_for_menu_closed()
        field = None
        try:
            field = yata.wait(
                lambda: yata.window.find(role="text", states={"editable", "focused"}),
                "the compress name field to take focus",
                timeout=5,
            )
        except tree.TreeTimeout:
            pass
        if field is not None:
            yata.keyboard.press("ctrl+a")
            yata.keyboard.type_text(archive_name)
            yata.wait(
                lambda: field.text == archive_name,
                f"{archive_name!r} to reach the name field",
            )
            yata.keyboard.press("Return")
            yata.wait(lambda: yata.dialog() is None, "the dialog to close")
            path = yata.fixture.path(folder).joinpath(f"{archive_name}.zip")
            yata.wait(lambda: path.exists(), "the archive to be created")
            return
    raise AssertionError("the compress dialog never accepted the archive name")


@pytest.mark.parametrize("mode", ALL_MODES)
def test_archive_far_from_viewport_is_scrolled_into_view(yata, mode):
    """A custom archive name that sorts far from the viewport still gets revealed."""
    yata.wait_for_view(mode)

    _compress(yata, "005.txt", "zzz", None)

    yata.wait_for_selection(["zzz.zip"])
    entry = yata.entry("zzz.zip")
    yata.wait(lambda: yata.on_screen(entry), "the distant archive to be on screen")


@pytest.mark.parametrize("mode", ALL_MODES)
def test_compressed_archive_is_revealed(yata, mode):
    """The archive lands at the end of the listing and must be scrolled into view."""
    yata.wait_for_view(mode)
    yata.keyboard.press("End")
    yata.wait_for_focused_entry("199.txt")

    _compress(yata, "199.txt", "199", None)

    yata.wait_for_selection(["199.zip"])
    entry = yata.entry("199.zip")
    yata.wait(lambda: yata.on_screen(entry), "the new archive to be on screen")


def test_columns_reveals_archive_in_active_child_column(yata):
    """Columns mode scrolls the archive into view inside the open child column."""
    yata.wait_for_view("Columns")
    yata.open_directory("nested")
    yata.keyboard.press("End")
    yata.wait_for_focused_entry("199.txt")

    _compress(yata, "199.txt", "199", "nested", folder="nested")

    yata.wait_for_selection(["199.zip"], directory="nested")
    entry = yata.entry("199.zip", directory="nested")
    yata.wait(
        lambda: yata.on_screen(entry),
        "the archive to be on screen in the child column",
    )


def test_columns_reveals_archive_in_deeply_nested_column(yata):
    """Columns mode scrolls horizontally and vertically to the archive in a deep column."""
    yata.wait_for_view("Columns")
    yata.open_directory("a")
    yata.open_directory("b", directory="a")
    yata.open_directory("c", directory="b")
    yata.open_directory("d", directory="c")
    yata.keyboard.press("End")
    yata.wait_for_focused_entry("199.txt")

    _compress(yata, "199.txt", "199", "d", folder="a/b/c/d")

    yata.wait_for_selection(["199.zip"], directory="d")
    entry = yata.entry("199.zip", directory="d")
    yata.wait(
        lambda: yata.on_screen(entry),
        "the archive to be on screen in the deep column",
    )


def test_columns_reveals_archive_in_parent_column(yata):
    """Columns mode scrolls an archive created in a non-active parent column."""
    root = yata.fixture.root.name
    yata.wait_for_view("Columns")
    yata.open_directory("nested")
    yata.keyboard.press("Left")
    yata.wait_for_focused_entry("nested")
    yata.keyboard.press("End")
    yata.wait_for_focused_entry("199.txt")

    _compress(yata, "199.txt", "199", root)

    yata.wait_for_selection(["199.zip"], directory=root)
    entry = yata.entry("199.zip", directory=root)
    yata.wait(
        lambda: yata.on_screen(entry),
        "the archive to be on screen in the parent column",
    )