# SPDX-License-Identifier: MIT
"""Opening, reading, and closing the quick preview."""

from __future__ import annotations

import pytest

from harness.fixtures import FixtureTree
from harness.modes import ALL_MODES, NEXT_ENTRY_KEY, PREVIOUS_ENTRY_KEY

PREVIEW_FIXTURE = {
    "notes.txt": "the quick brown fox\n",
    "page.md": "# Heading\n\nBody text.\n",
    "third.txt": "third preview fixture\n",
    "data.csv": "name,value\nalpha,1\n",
    "folder": {"inner.txt": "inner\n", "nested-notes.txt": "nested preview fixture\n"},
}


@pytest.fixture
def fixture_tree():
    """Replaces the shared fixture with file types the preview can render."""

    tree = FixtureTree.create(PREVIEW_FIXTURE)
    try:
        yield tree
    finally:
        tree.cleanup()


@pytest.mark.parametrize(
    "mode,selection",
    [
        pytest.param(
            "Columns",
            "keyboard",
            marks=pytest.mark.preferences(browser_mode="columns"),
            id="columns-keyboard",
        ),
        pytest.param(
            "Icons",
            "keyboard",
            marks=pytest.mark.preferences(browser_mode="icons"),
            id="icons-keyboard",
        ),
        pytest.param(
            "List",
            "keyboard",
            marks=pytest.mark.preferences(browser_mode="list"),
            id="list-keyboard",
        ),
        pytest.param(
            "List",
            "pointer",
            marks=pytest.mark.preferences(browser_mode="list"),
            id="list-pointer",
        ),
    ],
)
def test_space_opens_and_closes_the_quick_preview(yata, mode, selection):
    before = yata.entry_names()
    if selection == "keyboard":
        yata.select_entry_with_keyboard("notes.txt")
    else:
        yata.select_entry("notes.txt")

    yata.keyboard.press("space")

    yata.wait(
        lambda: yata.preview_shows("the quick brown fox"),
        "the preview to render the file's text",
    )

    preview = yata.preview()
    assert preview.find(role="label", name="notes.txt") is not None
    assert yata.preview_shows("text/plain")
    assert yata.entry_names() == before
    close = preview.find(role="button", name="Close preview (Space)")
    yata.pointer.click(close)
    yata.wait(lambda: yata.preview() is None, "the preview to close")


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("selection", ["keyboard", "pointer"])
def test_space_previews_a_filtered_result_without_changing_the_query(yata, mode, selection):
    yata.select_entry("notes.txt")
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    yata.keyboard.type_text("nested-notes")
    yata.wait(
        lambda: yata.matches() == ["nested-notes.txt"],
        "the nested search result",
    )
    if selection == "keyboard":
        yata.keyboard.press("Down")
    else:
        result = yata.window.find(name="nested-notes.txt", role="list item")
        assert result is not None
        yata.pointer.click(result, modifiers=("ctrl",))

    yata.keyboard.press("space")
    yata.wait(
        lambda: yata.preview_shows("nested preview fixture"),
        "Space to preview the search result, not the stale directory selection",
    )
    assert field.text == "nested-notes"
    assert yata.matches() == ["nested-notes.txt"]
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview() is None, "Space to close the filtered preview")
    assert field.text == "nested-notes"
    assert yata.matches() == ["nested-notes.txt"]


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("selection", ["keyboard", "pointer"])
def test_preview_follows_the_selection(yata, mode, selection):
    yata.select_entry_with_keyboard("notes.txt")
    yata.keyboard.press("space")
    yata.wait(
        lambda: yata.preview_shows("the quick brown fox"),
        "the first preview to render",
    )

    if selection == "keyboard":
        yata.keyboard.press(NEXT_ENTRY_KEY[mode])
    else:
        yata.select_entry("page.md")
    yata.wait_for_selection(["page.md"])

    yata.wait(
        lambda: yata.preview_shows("Body text."),
        "the preview to follow the newly selected file",
    )
    assert yata.focused_name() == "page.md"
    assert not yata.preview_shows("the quick brown fox")


def test_list_preview_keyboard_navigation_preserves_horizontal_scroll(yata, fixture_tree):
    yata.switch_view("List")
    yata.select_entry_with_keyboard("notes.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("the quick brown fox"), "the first preview")

    def list_scroll_origin():
        container = yata.pane()
        list_view = container.find(description="Files")
        assert list_view is not None, "the List file view"
        panes = [
            ancestor for ancestor in list_view.ancestors() if ancestor.role == "scroll pane"
        ]
        assert len(panes) >= 2, "the List view content is wrapped by its listing scroller"
        return panes[0].window_bounds().x

    origin = list_scroll_origin()
    for key, name, preview in (
        ("Down", "page.md", "Body text."),
        ("Down", "third.txt", "third preview fixture"),
        ("Up", "page.md", "Body text."),
    ):
        yata.keyboard.press(key)
        yata.wait_for_selection([name])
        yata.wait(lambda: yata.focused_name() == name, f"focus on {name}")
        yata.wait(lambda: yata.preview_shows(preview), f"preview for {name}")
        assert list_scroll_origin() == origin, (origin, list_scroll_origin())


@pytest.mark.parametrize("mode", ALL_MODES)
def test_preview_follows_extended_selection_without_collapsing_it(yata, mode):
    yata.select_entry_with_keyboard("notes.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("the quick brown fox"), "the first preview")

    yata.keyboard.press(f"shift+{NEXT_ENTRY_KEY[mode]}")

    yata.wait_for_selection(["notes.txt", "page.md"])
    yata.wait(lambda: yata.preview_shows("Body text."), "the newly focused preview")
    assert yata.focused_name() == "page.md"


@pytest.mark.parametrize("mode", ALL_MODES)
def test_preview_hides_on_a_folder_and_resumes_when_selection_moves(yata, mode):
    yata.select_entry_with_keyboard("data.csv")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("alpha"), "the file preview")

    yata.keyboard.press(PREVIOUS_ENTRY_KEY[mode])

    yata.wait_for_selection(["folder"])
    if mode == "Icons":
        yata.wait(lambda: yata.preview_shows("No preview for this selection"), "the folder's reserved preview space")
    else:
        yata.wait(lambda: yata.preview() is None, "the folder to dismiss the preview")
    yata.keyboard.press(NEXT_ENTRY_KEY[mode])
    yata.wait_for_selection(["data.csv"])
    yata.wait(lambda: yata.preview_shows("alpha"), "the still-enabled preview to resume")


def test_preview_hides_on_shift_range_folder_focus(yata):
    yata.switch_view("List")
    yata.select_entry_with_keyboard("notes.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("the quick brown fox"), "the file preview")

    yata.keyboard.press("shift+Up")
    yata.wait_for_selection(["data.csv", "notes.txt"])
    yata.wait(lambda: yata.focused_name() == "data.csv", "the focused upper file")
    yata.wait(lambda: yata.preview_shows("alpha"), "the upper file preview")

    yata.keyboard.press("shift+Up")
    yata.wait_for_selection(["folder", "data.csv", "notes.txt"])
    yata.wait(lambda: yata.focused_name() == "folder", "the focused folder")
    yata.wait(lambda: yata.preview() is None, "the focused folder to dismiss the preview")

    yata.keyboard.press("shift+Down")
    yata.wait_for_selection(["data.csv", "notes.txt"])
    yata.wait(lambda: yata.preview_shows("alpha"), "preview to resume after the folder")


def test_preview_renders_markdown(yata):
    yata.select_entry_with_keyboard("page.md")
    yata.keyboard.press("space")

    yata.wait(
        lambda: yata.preview_shows("Body text."),
        "the markdown preview to render its body",
    )


@pytest.mark.preferences(browser_mode="columns", single_click_previews=False)
def test_column_preview_fills_free_space_and_remembers_a_dragged_session_width(yata):
    def adjacent():
        column = yata.containers()[-1].screen_bounds()
        preview = yata.preview().screen_bounds()
        return abs(preview.x - (column.x + column.width)) <= 3

    yata.select_entry_with_keyboard("notes.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("the quick brown fox"), "the first preview")
    yata.wait(adjacent, "the preview to meet the last column")
    initial = yata.preview().screen_bounds().width
    yata.keyboard.press("Down")
    yata.wait(lambda: yata.preview_shows("Body text."), "keyboard selection to update the preview")
    yata.keyboard.press("space")
    yata.open_directory("folder")
    yata.select_entry_with_keyboard("inner.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("inner"), "the nested preview")
    yata.wait(adjacent, "columns to scroll left beside the minimum-width preview")
    minimum = yata.preview().screen_bounds().width
    assert minimum < initial
    assert yata.containers()[0].screen_bounds().x < yata.pane("folder").screen_bounds().x

    bounds = yata.preview().screen_bounds()
    start = (bounds.x - 1, bounds.y + bounds.height // 2)
    distance = bounds.width // 5
    yata.pointer.drag_points(start, (start[0] + distance, start[1]))
    yata.wait(
        lambda: yata.preview().screen_bounds().width < minimum - distance // 2,
        "the dragged width to override the automatic minimum",
    )
    chosen = yata.preview().screen_bounds().width
    resized = yata.preview().screen_bounds()
    window = yata.window_bounds()
    assert abs(resized.x + resized.width - window.x - window.width) <= 2
    yata.keyboard.press("space")
    yata.select_entry_with_keyboard("nested-notes.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("nested preview fixture"), "the reopened preview")
    assert abs(yata.preview().screen_bounds().width - chosen) <= 2
    yata.keyboard.press("space")
    yata.keyboard.press("alt+Left")
    yata.select_entry_with_keyboard("notes.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("the quick brown fox"), "the parent preview")
    assert abs(yata.preview().screen_bounds().width - chosen) <= 2


@pytest.mark.preferences(browser_mode="columns", single_click_previews=False)
def test_closing_preview_does_not_move_the_columns(yata):
    yata.open_directory("folder")
    yata.select_entry_with_keyboard("inner.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("inner"), "the nested preview")
    column = yata.pane("folder")
    scroller = next(node for node in column.ancestors() if node.role == "scroll pane")
    before = column.screen_bounds()
    viewport_width = scroller.screen_bounds().width
    close = yata.preview().find(role="button", name="Close preview (Space)")
    yata.pointer.click(close)
    yata.wait(lambda: yata.preview() is None, "the preview to close")
    yata.wait(lambda: scroller.screen_bounds().width > viewport_width, "the browser to use the released space")
    assert abs(yata.pane("folder").screen_bounds().x - before.x) <= 1
    yata.select_entry("inner.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("inner"), "the preview to reopen")
    yata.wait(
        lambda: abs(yata.pane("folder").screen_bounds().x + before.width - yata.preview().screen_bounds().x) <= 3,
        "the reopened preview to meet the last column",
    )


@pytest.mark.preferences(browser_mode="columns", single_click_previews=False)
def test_narrow_window_prioritizes_the_last_column_and_restores_the_latest_preview(yata):
    browser_left = yata.pane().screen_bounds().x
    yata.open_directory("folder")
    yata.select_entry_with_keyboard("inner.txt")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("inner"), "the initial preview")
    preferred = yata.preview().screen_bounds().width

    def resize(width):
        bounds = yata.window_bounds()
        yata.keyboard.connection.resize_surface(bounds.width, bounds.height, width, bounds.height)
        yata.wait(lambda: yata.window_bounds().width == width, "the resized window")

    def last_column_visible():
        column = yata.pane("folder").screen_bounds()
        window = yata.window_bounds()
        return column.x >= browser_left and column.x + column.width <= window.x + window.width

    resize(900)
    yata.wait(lambda: yata.preview().screen_bounds().width < preferred, "the preview minimum to yield")
    yata.wait(last_column_visible, "the entire last column to stay visible")
    column = yata.pane("folder").screen_bounds()
    assert column.x + column.width <= yata.preview().screen_bounds().x
    resize(760)
    yata.wait(lambda: yata.preview() is None, "the unusably narrow preview to hide")
    yata.wait(last_column_visible, "the last column without the preview")
    yata.keyboard.press("Down")
    yata.wait_for_selection(["nested-notes.txt"])
    assert yata.preview() is None
    resize(900)
    yata.wait(lambda: yata.preview_shows("nested preview fixture"), "the latest selection to resume")
    yata.wait(last_column_visible, "the last column beside the resumed preview")
    resize(1200)
    yata.wait(lambda: yata.preview().screen_bounds().width == preferred, "the preferred preview width to return")
