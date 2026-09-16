# SPDX-License-Identifier: MIT
"""Content drags, inert-space marquees, and release-only previews in every mode."""

import pytest

from harness.artifacts import ArtifactCollector
from harness.modes import ALL_MODES


@pytest.mark.preferences(single_click_previews=True)
@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("origin", ["icon", "name"])
def test_file_drag_does_not_open_preview(yata, mode, origin):
    source = yata.entry("todo.txt")
    if origin == "icon":
        start = yata.pointer.drag_origin(source)
    else:
        label = source.find(role="label", name="todo.txt")
        assert label is not None
        bounds = label.screen_bounds()
        start = bounds.center if mode == "Icons" else (bounds.x + 4, bounds.center[1])
    target = yata.entry("archive")

    def assert_no_preview_on_press():
        yata.entry("todo.txt")
        assert yata.preview() is None, "a held press must not open a preview"

    yata.pointer.drag_points(
        start, target.screen_bounds().center, release=False,
        after_press=assert_no_preview_on_press,
    )
    try:
        assert yata.preview() is None, "crossing the drag threshold must suppress preview"
    finally:
        yata.pointer.connection.button(1, False)
    yata.wait(lambda: yata.fixture.path("archive/todo.txt").exists(), "the file drop")
    assert not yata.fixture.path("todo.txt").exists()
    assert yata.preview() is None


@pytest.mark.preferences(single_click_previews=True)
@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("origin", ["content", "inert"])
def test_simple_click_still_opens_preview(yata, mode, origin):
    at = _inert_point(yata, "todo.txt", mode) if origin == "inert" else None
    yata.pointer.click(yata.entry("todo.txt"), at=at)
    yata.wait(lambda: yata.preview_shows("todo"), "preview after a simple click")


def _full_directory(yata):
    folder = yata.fixture.path("full")
    folder.mkdir()
    for index in range(180):
        (folder / f"{index:03}.txt").write_text(f"{index}\n")
    yata.open_directory("full")
    return folder


def _inert_point(yata, name, mode):
    row = yata.entry(name)
    if mode == "Icons":
        icon = row.find(role="image")
        assert icon is not None
        bounds = icon.screen_bounds()
        return bounds.x - 6, bounds.center[1]
    label = row.find(role="label", name=name)
    assert label is not None
    bounds = label.screen_bounds()
    return bounds.x + bounds.width * 2 // 3, bounds.center[1]


@pytest.mark.preferences(single_click_previews=True)
@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize(
    "modifiers",
    [pytest.param((), id="plain"), pytest.param(("ctrl",), id="ctrl")],
)
def test_marquee_begins_beside_content_in_a_full_pane(yata, mode, modifiers):
    folder = _full_directory(yata)
    before = sorted(folder.iterdir())
    initial = set(yata.selected_names())
    start = _inert_point(yata, "000.txt", mode)
    end = _inert_point(yata, "010.txt", mode)
    drag_modifiers = (*modifiers, "alt") if mode == "Columns" else modifiers
    yata.pointer.drag_points(
        start, (end[0] + 3, end[1]), modifiers=drag_modifiers
    )

    yata.wait(
        lambda: len(yata.selected_names()) > 1,
        "marquee selection beside occupied rows",
    )
    selected = set(yata.selected_names())
    for name in ("000.txt", "010.txt"):
        expected = name not in initial if "ctrl" in modifiers else True
        assert (name in selected) == expected
    assert yata.preview() is None
    assert sorted(folder.iterdir()) == before


@pytest.mark.preferences(browser_mode="icons")
@pytest.mark.parametrize("text_size", [
    pytest.param(13, marks=pytest.mark.preferences(text_size=13)),
    pytest.param(28, marks=pytest.mark.preferences(text_size=28)),
])
@pytest.mark.parametrize("corner", ["leading", "trailing"])
def test_pane_corner_marquee_does_not_resize_sidebar(yata, text_size, corner):
    folder = _full_directory(yata)
    before = sorted(folder.iterdir())
    sidebar = yata.sidebar_button("Home").parent
    while sidebar is not None and sidebar.role != "scroll pane":
        sidebar = sidebar.parent
    assert sidebar is not None
    sidebar_before = sidebar.screen_bounds()
    pane = yata.pane().screen_bounds()
    container = yata.entry_container().screen_bounds()
    x = pane.x + 2 if corner == "leading" else container.x + container.width - 2
    start = (x, container.y + 2)
    end = yata.entry("002.txt").screen_bounds().center
    yata.pointer.drag_points(start, end)
    yata.settle(yata.pane())
    assert sidebar.screen_bounds().width == sidebar_before.width, (
        f"{text_size}px {corner} pane corner must select files, not resize the sidebar"
    )
    yata.wait(
        lambda: "002.txt" in yata.selected_names() and len(yata.selected_names()) > 1,
        "a marquee from the pane corner to select files",
    )
    selected = yata.selected_names()
    divider = ((sidebar_before.x + sidebar_before.width + pane.x) // 2, container.center[1])
    yata.pointer.drag_points(divider, (divider[0] + 40, divider[1]))
    yata.wait(
        lambda: sidebar.screen_bounds().width >= sidebar_before.width + 30,
        "dragging the actual sidebar divider to resize it",
    )
    assert yata.selected_names() == selected
    assert sorted(folder.iterdir()) == before


@pytest.mark.parametrize("mode", ALL_MODES)
def test_modifier_clicks_on_inert_space_still_select(yata, mode):
    _full_directory(yata)
    yata.select_entry("000.txt")
    yata.pointer.click(
        yata.entry("002.txt"),
        at=_inert_point(yata, "002.txt", mode),
        modifiers=("ctrl",),
    )
    yata.wait_for_selection(["000.txt", "002.txt"])
    yata.pointer.click(
        yata.entry("004.txt"),
        at=_inert_point(yata, "004.txt", mode),
        modifiers=("shift",),
    )
    yata.wait_for_selection(["002.txt", "003.txt", "004.txt"])


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize(
    "selected,open_after_drop",
    [
        pytest.param(
            False,
            False,
            marks=pytest.mark.preferences(open_folder_after_drop=False),
            id="unselected-stay",
        ),
        pytest.param(
            False,
            True,
            marks=pytest.mark.preferences(open_folder_after_drop=True),
            id="unselected-open",
        ),
        pytest.param(
            True,
            False,
            marks=pytest.mark.preferences(open_folder_after_drop=False),
            id="selected-stay",
        ),
    ],
)
def test_ctrl_drag_from_content_copies_and_keeps_selection(
    yata, mode, selected, open_after_drop,
):
    if selected:
        yata.select_entry("todo.txt")
    initial_selection = yata.selected_names()
    start = yata.pointer.drag_origin(yata.entry("todo.txt"))
    target = yata.entry("archive")
    yata.pointer.drag_points(
        start, target.screen_bounds().center, modifiers=("ctrl",)
    )
    yata.wait(
        lambda: yata.fixture.path("archive/todo.txt").exists(),
        "the ctrl-drag from content to copy the file",
    )
    assert yata.fixture.path("todo.txt").exists()
    if open_after_drop:
        yata.entry("todo.txt", directory="archive")
        yata.wait_for_selection(["todo.txt"])
    else:
        # Pre-selecting the source does not keep the listing selection after drop.
        if not selected:
            yata.wait_for_selection(sorted(set(initial_selection) | {"todo.txt"}))
        yata.entry("todo.txt", directory=yata.fixture.root.name)
        assert "archive" not in yata.pane_names()


@pytest.mark.parametrize("mode", ALL_MODES)
def test_shift_drag_from_content_moves_the_file(yata, mode):
    start = yata.pointer.drag_origin(yata.entry("todo.txt"))
    target = yata.entry("archive")
    yata.pointer.drag_points(
        start, target.screen_bounds().center, modifiers=("shift",)
    )
    yata.wait(
        lambda: yata.fixture.path("archive/todo.txt").exists(),
        "the shift-drag from content to move the file",
    )
    assert not yata.fixture.path("todo.txt").exists()


@pytest.mark.parametrize("mode", ALL_MODES)
def test_sidebar_marquee_still_reaches_the_leading_pane(yata, mode):
    root = yata.fixture.root.name
    if mode == "Columns":
        yata.open_directory("documents")
    home = yata.sidebar_button("Home")
    for _ in range(2):
        yata.keyboard.press("Home")
        yata.keyboard.press("Left")
        if home.has_state("focused"):
            break
    yata.wait(lambda: home.has_state("focused"), "keyboard focus in the sidebar")
    sidebar = home.parent
    assert sidebar is not None
    bounds = sidebar.screen_bounds()
    start = (bounds.center[0], bounds.y + bounds.height - 10)
    first = yata.entry("readme.md", root).screen_bounds().center
    last = yata.entry("todo.txt", root).screen_bounds().center
    yata.pointer.drag_points(start, (last[0], first[1]), release=False)
    try:
        yata.wait(
            lambda: {"readme.md", "todo.txt"} <= set(yata.selected_names(root)),
            "the sidebar marquee to select in the leading pane",
        )
        collection = yata.entry_container(root)
        yata.wait(
            lambda: any(node.has_state("focused") for _, node in collection.walk()),
            "the marquee target to own focus and active selection feedback during the drag",
        )
        yata.screenshot(
            ArtifactCollector(test_name=f"sidebar-marquee-{mode}").directory
            / "selection.png"
        )
    finally:
        yata.pointer.connection.button(1, False)
    assert not home.has_state("focused")
    selected = set(yata.selected_names(root))
    yata.keyboard.press("ctrl+c")
    destination = "selection-copy"
    yata.fixture.path(destination).mkdir()
    yata.open_directory(destination, root)
    yata.paste_into(destination)
    yata.wait(
        lambda: set(yata.fixture.names(destination)) == selected
        and all(
            yata.fixture.path(f"{destination}/{name}").stat().st_size
            == yata.fixture.path(name).stat().st_size
            for name in ("readme.md", "todo.txt")
        ),
        "keyboard copy to finish in the marquee target rather than the sidebar or another pane",
    )
    for name in ("readme.md", "todo.txt"):
        assert yata.fixture.path(f"{destination}/{name}").read_bytes() == yata.fixture.path(
            name
        ).read_bytes()
