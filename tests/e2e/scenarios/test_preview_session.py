# SPDX-License-Identifier: MIT
import pytest
from PIL import Image

from harness.fixtures import FixtureTree
from harness.modes import ALL_MODES


@pytest.fixture
def fixture_tree():
    tree = FixtureTree.create({
        "a.txt": "root preview\n",
        "z.zip": "unsupported fixture\n",
        "Alpha": {"a.txt": "alpha preview\n", "Beta": {"Gamma": {"Delta": {"a.txt": "delta preview\n"}}}},
    })
    Image.new("RGB", (80, 40), "green").save(tree.path("image.png"))
    try:
        yield tree
    finally:
        tree.cleanup()


def preview_option(yata):
    yata.open_appearance_menu()
    return yata.wait(
        lambda: yata.window.find(role="toggle button", name="Preview panel"),
        "the session preview toggle",
    )


@pytest.mark.parametrize("mode", ALL_MODES)
def test_preview_mode_survives_unsupported_selections_and_matches_appearance(yata, mode):
    yata.switch_view(mode)
    yata.select_entry("z.zip")
    option = preview_option(yata)
    assert option.find(role="label", name="Space") is not None
    assert not option.has_state("pressed")
    yata.pointer.click(option)
    if mode == "Icons":
        yata.wait(lambda: yata.preview_shows("No preview for this selection"), "the reserved preview space")
    else:
        assert yata.preview() is None
    option = preview_option(yata)
    assert option.has_state("pressed"), option.states
    yata.dismiss_menu()
    yata.select_entry("a.txt")
    yata.wait(lambda: yata.preview_shows("root preview"), "automatic preview after ZIP")
    yata.select_entry_with_keyboard("z.zip")
    if mode == "Icons":
        yata.wait(lambda: yata.preview_shows("No preview for this selection"), "the empty preview slot")
    else:
        yata.wait(lambda: yata.preview() is None, "unsupported selection to hide the panel")
    option = preview_option(yata)
    assert option.has_state("pressed"), option.states
    yata.pointer.click(option)
    yata.select_entry("a.txt")
    assert yata.preview() is None
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("root preview"), "Space to enable the panel")
    option = preview_option(yata)
    assert option.has_state("pressed"), option.states
    yata.dismiss_menu()
    yata.open_directory("Alpha")
    yata.select_entry_with_keyboard("a.txt")
    yata.wait(lambda: yata.preview_shows("alpha preview"), "preview after directory navigation")
    yata.select_entry_with_keyboard("Beta")
    yata.keyboard.press("space")
    if mode == "Columns":
        yata.wait_for_directory("Beta")
    option = preview_option(yata)
    assert option.has_state("pressed") == (mode == "Columns")
    yata.dismiss_menu()
    assert yata.current_directory() == ("Beta" if mode == "Columns" else "Alpha")


@pytest.mark.preferences(browser_mode="icons", single_click_previews=False)
def test_icons_keep_their_layout_until_preview_mode_is_explicitly_toggled(yata):
    yata.select_entry("a.txt")
    full_width = yata.pane().screen_bounds().width
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("root preview"), "the initial preview")
    width = yata.pane().screen_bounds().width
    assert width < full_width

    def positions():
        return {name: yata.entry(name).screen_bounds() for name in ["Alpha", "a.txt", "image.png", "z.zip"]}

    layout = positions()

    def assert_layout():
        for name, actual in positions().items():
            expected = layout[name]
            assert abs(actual.x - expected.x) <= 1 and abs(actual.y - expected.y) <= 1, (name, expected, actual)
            assert actual.width == expected.width and actual.height == expected.height

    for name, expected in [("z.zip", "No preview for this selection"), ("image.png", "image/png"), ("Alpha", "No preview for this selection"), ("a.txt", "root preview")]:
        yata.select_entry_with_keyboard(name)
        yata.wait(lambda: yata.preview_shows(expected), f"the preview for {name}")
        assert yata.pane().screen_bounds().width == width
        assert_layout()
        if name in ["z.zip", "Alpha"]:
            assert not yata.preview_shows("root preview")
            assert yata.preview().find(role="label", name="a.txt") is None
            assert not yata.preview().find(role="button", name="Open in default application").has_state("sensitive")

    yata.pointer.click(yata.pane(), at=yata.background_point())
    yata.wait_for_selection([])
    yata.wait(lambda: yata.preview_shows("No preview for this selection"), "empty selection without reflow")
    assert_layout()
    yata.open_directory("Alpha")
    yata.wait(lambda: yata.preview_shows("No preview for this selection"), "the folder's preview slot")
    assert yata.pane().screen_bounds().width == width
    yata.select_entry("a.txt")
    yata.wait(lambda: yata.preview_shows("alpha preview"), "a preview inside the folder")
    assert yata.pane().screen_bounds().width == width
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview() is None and yata.pane().screen_bounds().width == full_width, "intentional toggle to restore the full grid")
    for name in ["Beta", "a.txt"]:
        yata.select_entry(name)
        assert yata.preview() is None
        assert yata.pane().screen_bounds().width == full_width


@pytest.mark.preferences(browser_mode="columns", single_click_previews=False)
def test_peek_click_reveals_a_column_without_activating_rows_or_toolbar_actions(yata):
    browser_left = yata.pane().screen_bounds().x
    for name in ["Alpha", "Beta", "Gamma", "Delta"]:
        yata.open_directory(name)
    def pane_count():
        return len(yata.window.find_all(description="Columns view", rendered=False))

    before = pane_count()
    peek = yata.wait(
        lambda: yata.window.find(role="button", name="Reveal Alpha column"),
        "a clickable parent-column peek",
    )
    bounds = peek.screen_bounds()
    heading = yata.pane("Alpha").find(role="label", name="Alpha", rendered=False)
    assert heading is not None
    yata.pointer.double_click(peek, at=(bounds.center[0], heading.screen_bounds().center[1]))
    yata.wait(lambda: yata.focused_name() == "Beta", "focus in the revealed parent")
    assert pane_count() == before
    yata.wait(
        lambda: yata.pane("Alpha").screen_bounds().x >= yata.sidebar_button("Home").screen_bounds().x,
        "the entire focused parent",
    )
    child = yata.wait(
        lambda: yata.window.find(role="button", name="Reveal Delta column"),
        "a clickable right-hand column peek",
    )
    yata.pointer.click(child)
    yata.wait(lambda: yata.pane("Delta").screen_bounds().x + yata.pane("Delta").screen_bounds().width <= yata.window_bounds().width, "the revealed child column")
    assert pane_count() == before
    parent = yata.wait(lambda: yata.window.find(role="button", name="Reveal Alpha column"), "the parent peek again")
    yata.pointer.click(parent)
    yata.wait(lambda: yata.focused_name() == "Beta", "the parent to receive focus")
    yata.select_entry("a.txt", directory="Alpha")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("alpha preview"), "the focused parent's preview")

    def focused_column_fits():
        column = yata.pane("Alpha").screen_bounds()
        return column.x >= browser_left and column.x + column.width <= yata.preview().screen_bounds().x

    yata.wait(focused_column_fits, "the focused parent, not the rightmost column, to remain visible")
    assert pane_count() == before
