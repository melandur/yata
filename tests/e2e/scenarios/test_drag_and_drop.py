# SPDX-License-Identifier: MIT
"""Moving entries by dragging them between folders."""

from __future__ import annotations

import pytest

from harness.modes import ALL_MODES


@pytest.mark.parametrize("mode", ALL_MODES)
def test_dragging_a_file_onto_a_folder_moves_it(yata, mode):
    fixture = yata.fixture
    source = yata.select_entry("todo.txt")
    target = yata.entry("archive")

    yata.pointer.drag(source, target)

    yata.wait(
        lambda: fixture.path("archive/todo.txt").exists(),
        "the dragged file to arrive in archive",
    )
    yata.wait(
        lambda: not fixture.path("todo.txt").exists(),
        "the dragged file to leave its source directory",
    )
    yata.wait_for_entry_gone("todo.txt", directory=yata.fixture.root.name)
    assert fixture.path("archive/todo.txt").read_text() == "todo\n"


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("recursive", [
    pytest.param(False, marks=pytest.mark.preferences(filter_include_subfolders=False)),
    pytest.param(True, marks=pytest.mark.preferences(filter_include_subfolders=True)),
])
def test_dragging_a_filtered_result_to_a_sidebar_folder(yata, mode, recursive):
    source_path = (
        next(yata.fixture.root.rglob("spreadsheet.csv"))
        if recursive else yata.fixture.path("todo.txt")
    )
    contents = source_path.read_bytes()
    destination = yata.environment.home / source_path.name
    yata.keyboard.press("ctrl+f")
    yata.keyboard.type_text(source_path.name)
    source = yata.wait(
        lambda: yata.window.find(role="list item", name=source_path.name),
        "the filtered drag source",
    )
    yata.pointer.drag(source, yata.sidebar_button("Home"))
    yata.wait(lambda: destination.exists(), "the filtered file to arrive in Home")
    yata.wait(lambda: not source_path.exists(), "the filtered source to be moved")
    assert destination.read_bytes() == contents
    yata.wait(
        lambda: yata.window.find(role="list item", name=source_path.name) is None,
        "the moved result to leave the filtered listing",
    )


def test_dropping_a_file_on_itself_changes_nothing(yata):
    fixture = yata.fixture
    before = fixture.listing()
    source = yata.select_entry("todo.txt")

    yata.pointer.drag(source, source)

    yata.entry("todo.txt")
    assert fixture.listing() == before, (
        "dropping an entry on itself must not move anything"
    )


@pytest.mark.parametrize("mode", ALL_MODES)
def test_dropping_a_folder_into_itself_changes_nothing(yata, mode):
    fixture = yata.fixture
    before = fixture.listing()
    source = yata.select_entry("documents")

    yata.pointer.drag(source, source)

    yata.entry("documents")
    assert fixture.listing() == before, (
        "a folder must not be moved inside itself"
    )
    assert fixture.path("documents/notes.txt").exists()


def test_releasing_outside_the_window_cancels_the_drag(yata):
    """The drag crosses a real drop target, then ends where none exists."""

    fixture = yata.fixture
    before = fixture.listing()
    source = yata.select_entry("todo.txt")
    window = yata.window.screen_bounds()
    outside = (window.x + window.width + 60, window.y + window.height + 40)

    yata.pointer.abandon_drag(source, outside)

    yata.entry("todo.txt")
    assert fixture.listing() == before, (
        "a drag released outside every drop target must not move anything"
    )


def test_dragging_onto_the_pane_background_is_a_no_op(yata):
    """Dropping an entry back into the directory it already lives in."""

    fixture = yata.fixture
    before = fixture.listing()
    source = yata.select_entry("todo.txt")
    pane = yata.pane()
    bounds = pane.screen_bounds()
    empty_point = (bounds.x + bounds.width // 2, bounds.y + bounds.height - 20)

    yata.pointer.drag_to_point(source, empty_point)

    yata.entry("todo.txt")
    assert fixture.listing() == before, (
        "dropping into the same directory must not duplicate or move anything"
    )


def test_dragging_a_folder_into_another_folder_moves_its_contents(yata):
    fixture = yata.fixture
    source = yata.select_entry("pictures")
    yata.entry("photo.txt", directory="pictures")
    yata.settle(source)
    target = yata.entry("archive")

    yata.pointer.drag(source, target)

    yata.wait(
        lambda: fixture.path("archive/pictures/photo.txt").exists(),
        "the dragged folder to arrive with its contents",
    )
    yata.wait(
        lambda: not fixture.path("pictures").exists(),
        "the dragged folder to leave its source directory",
    )
    assert sorted(fixture.names("archive/pictures")) == ["diagram.txt", "photo.txt"]


def test_dragging_a_multi_selection_moves_every_entry(yata):
    fixture = yata.fixture
    yata.select_entry("readme.md")
    yata.keyboard.press("shift+Down")
    yata.wait(
        lambda: yata.selected_names() == ["readme.md", "todo.txt"],
        "both files to be selected",
    )

    yata.pointer.drag(yata.entry("todo.txt"), yata.entry("archive"))

    yata.wait(
        lambda: fixture.path("archive/todo.txt").exists()
        and fixture.path("archive/readme.md").exists(),
        "both dragged files to arrive in archive",
    )
    assert not fixture.path("todo.txt").exists()
    assert not fixture.path("readme.md").exists()


ROW_DRAG_MODES = [
    mode for mode in ALL_MODES if mode.id != "icons"
]


@pytest.mark.preferences(single_click_previews=True)
@pytest.mark.parametrize("mode", ROW_DRAG_MODES)
def test_empty_name_space_drag_respects_view_policy(yata, mode):
    """Columns keep whole-row dragging; List name whitespace starts selection."""

    fixture = yata.fixture
    source = yata.entry("todo.txt")
    target = yata.entry("archive")
    start = yata.pointer.row_whitespace_point(source, "todo.txt")

    yata.pointer.drag_points(start, target.screen_bounds().center)

    if mode == "List":
        expect_name_space_marquee(yata)
        return
    yata.wait(
        lambda: fixture.path("archive/todo.txt").exists(),
        "the file dragged from empty row space to arrive in archive",
    )
    yata.wait(
        lambda: not fixture.path("todo.txt").exists(),
        "the file dragged from empty row space to leave its source directory",
    )


def expect_name_space_marquee(yata):
    yata.wait(
        lambda: {"archive", "todo.txt"} <= set(yata.selected_names()),
        "name-column whitespace to select files rather than move one",
    )
    assert yata.fixture.path("todo.txt").exists()
    assert not yata.fixture.path("archive/todo.txt").exists()
    assert yata.preview() is None


def drag_from_row_padding(yata, mode, edge):
    fixture = yata.fixture
    source = yata.entry("todo.txt")
    target = yata.entry("archive")
    start = yata.pointer.row_padding_point(source, edge)
    if mode == "List":
        start = (yata.pointer.row_whitespace_point(source, "todo.txt")[0], start[1])

    yata.pointer.drag_points(start, target.screen_bounds().center)

    if mode == "List":
        expect_name_space_marquee(yata)
        source = yata.select_entry_with_keyboard("todo.txt")
        start = metadata_drag_origin(yata, source, edge)
        yata.pointer.drag_points(start, yata.entry("archive").screen_bounds().center)
    yata.wait(
        lambda: fixture.path("archive/todo.txt").exists(),
        f"the file dragged from {edge} row padding to arrive in archive",
    )
    yata.wait(
        lambda: not fixture.path("todo.txt").exists(),
        f"the file dragged from {edge} row padding to leave its source directory",
    )
    assert yata.preview() is None


@pytest.mark.preferences(single_click_previews=True)
@pytest.mark.parametrize("mode", ROW_DRAG_MODES)
@pytest.mark.parametrize("edge", ["top", "bottom"])
def test_row_padding_drag_respects_view_policy(yata, mode, edge):
    drag_from_row_padding(yata, mode, edge)


@pytest.mark.preferences(
    browser_density="airy", single_click_previews=True, browser_mode="list"
)
def test_airy_row_padding_drag_respects_view_policy(yata):
    drag_from_row_padding(yata, "List", "top")


def metadata_drag_origin(yata, source, edge=None):
    metadata = next(
        label for label in source.find_all(role="label")
        if label.name and label.name != "todo.txt"
    )
    bounds = metadata.screen_bounds()
    y = bounds.center[1] if edge is None else yata.pointer.row_padding_point(source, edge)[1]
    return bounds.x + 4, y


@pytest.mark.preferences(folder_peeking=True, browser_mode="icons")
def test_starting_a_drag_cancels_a_folder_peek(yata):
    """#621: a drag beginning must cancel any open folder peek in Icons view."""

    pane = yata.pane()
    pane_bounds = pane.screen_bounds()
    yata.pointer.move_to(pane_bounds.x + 20, pane_bounds.y + pane_bounds.height - 20)

    folder = yata.entry("archive")
    start = yata.pointer.drag_origin(folder)
    yata.pointer.move_to(*start)
    yata.wait(lambda: yata.peek() is not None, "the folder peek to open on hover")

    target = yata.entry("documents")
    yata.pointer.drag_points(start, target.screen_bounds().center, release=False)
    try:
        yata.wait(
            lambda: yata.peek() is None,
            "the peek to close when the drag starts",
        )
    finally:
        yata.pointer.connection.button(1, False)


@pytest.mark.preferences(browser_mode="columns", single_click_previews=False)
def test_dragging_from_a_clipped_column_in_a_narrow_window(yata):
    fixture = yata.fixture
    yata.open_directory("documents")

    bounds = yata.window.window_bounds()
    yata.keyboard.connection.resize_surface(bounds.width, bounds.height, 600, bounds.height)
    yata.wait(lambda: yata.window.window_bounds().width == 600, "a narrow window")

    source = yata.entry("notes.txt", directory="documents")
    destination = yata.environment.home / "notes.txt"

    yata.pointer.drag(source, yata.sidebar_button("Home"))

    yata.wait(lambda: destination.exists(), "the dragged file to arrive in Home")
    yata.wait(
        lambda: not fixture.path("documents/notes.txt").exists(),
        "the dragged file to leave the clipped column",
    )
    assert destination.read_text() == "notes\n"
