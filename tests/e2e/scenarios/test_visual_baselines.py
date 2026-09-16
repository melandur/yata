# SPDX-License-Identifier: MIT
"""Golden screenshots for a small set of deliberately stable states.

Interaction assertions are the primary gate; these catch rendering
regressions the accessible tree cannot see. Keep the set small: every image
here has to be reviewed whenever the design changes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from harness.fixtures import FixtureTree

BASELINE_FIXTURE = {
    "documents": {
        "notes.txt": "notes\n",
        "projects": {"release": {"summary.md": "# Release\n"}},
        "report.md": "# Report\n",
    },
    "pictures": {},
    "readme.md": "# Fixture\n",
    "todo.txt": "todo\n",
}

pytestmark = pytest.mark.baseline


# The breadcrumb and the context menu both render the fixture's path, so the
# baseline scenarios use a fixed directory instead of a randomized one.
BASELINE_ROOT = Path("/tmp/strata-e2e-baseline")
BASELINE_ENTRIES = ["documents", "pictures", "readme.md", "todo.txt"]
ICONS_BASELINE_FIXTURE = {
    "Applications": {},
    "DataGripProjects": {},
    "pictures": {},
    "readme.md": "# Fixture\n",
    "todo.txt": "todo\n",
}
ICONS_BASELINE_ENTRIES = [
    "Applications", "DataGripProjects", "pictures", "portrait.png", "readme.md",
    "todo.txt", "wide.png",
]
ICONS_BASELINE_THUMBNAILS = {
    "portrait.png": ((32, 64), (255, 140, 0)),
    "wide.png": ((64, 32), (70, 130, 180)),
}


@pytest.fixture
def fixture_tree(request):
    """Stable names and content, including mixed caption lengths and image shapes."""

    preferences = request.node.get_closest_marker("preferences")
    icons = preferences is not None and preferences.kwargs.get("browser_mode") == "icons"
    tree = FixtureTree.create_at(
        BASELINE_ROOT, ICONS_BASELINE_FIXTURE if icons else BASELINE_FIXTURE
    )
    if icons:
        for name, (size, color) in ICONS_BASELINE_THUMBNAILS.items():
            Image.new("RGB", size, color).save(BASELINE_ROOT / name)
    try:
        yield tree
    finally:
        tree.cleanup()


@pytest.mark.preferences(browser_mode="columns")
def test_columns_view_baseline(yata, baseline):
    _settle(yata)
    baseline(yata, "columns-view")


@pytest.mark.preferences(browser_mode="columns")
def test_columns_overflow_baseline(yata, baseline, tmp_path):
    yata.open_directory("documents")
    yata.open_directory("projects", "documents")
    yata.open_directory("release", "projects")
    _settle(yata, ["summary.md"])

    capture = yata.screenshot(tmp_path / "columns-overflow.png")
    sidebar = yata.sidebar_button("Home").parent
    assert sidebar is not None
    sidebar_bounds = sidebar.screen_bounds()
    pane_bounds = yata.pane("release").screen_bounds()
    leading_edge = sidebar_bounds.x + sidebar_bounds.width
    scrollbar_y = pane_bounds.y + pane_bounds.height + 7
    with Image.open(capture) as image:
        pixels = image.convert("RGB")
        assert pixels.getpixel((leading_edge, scrollbar_y)) == pixels.getpixel(
            (leading_edge + 20, scrollbar_y)
        ), "the horizontal scrollbar background should be continuous at its leading edge"

    baseline(yata, "columns-overflow")


@pytest.mark.preferences(browser_mode="icons")
def test_icons_view_baseline(yata, baseline, tmp_path):
    _settle_icons(yata, tmp_path)
    yata.select_entry_with_keyboard("DataGripProjects")
    baseline(yata, "icons-view")


@pytest.mark.preferences(browser_mode="icons", browser_density="airy")
def test_icons_airy_view_baseline(yata, baseline, tmp_path):
    _settle_icons(yata, tmp_path)
    yata.select_entry_with_keyboard("Applications")
    baseline(yata, "icons-airy-view")


@pytest.mark.preferences(browser_mode="icons")
def test_icons_hover_baseline(yata, baseline, tmp_path):
    _settle_icons(yata, tmp_path)
    yata.pointer.move_to(*yata.entry("todo.txt").screen_bounds().center)
    yata.settle(yata.pane())
    baseline(yata, "icons-hover")


@pytest.mark.preferences(browser_mode="list")
def test_list_view_baseline(yata, baseline):
    _settle(yata)
    baseline(yata, "list-view")


@pytest.mark.preferences(browser_mode="list")
def test_selection_and_focus_baseline(yata, baseline):
    yata.select_entry_with_keyboard("readme.md")
    yata.keyboard.press("shift+Down")
    yata.wait(
        lambda: yata.selected_names() == ["readme.md", "todo.txt"],
        "both files to be selected",
    )
    _settle(yata)
    baseline(yata, "selection-and-focus")


@pytest.mark.preferences(browser_mode="list")
def test_context_menu_baseline(yata, baseline):
    yata.open_context_menu("readme.md")
    yata.wait(
        lambda: "Copy" in yata.menu_items(), "the context menu to be populated"
    )
    baseline(yata, "context-menu")


@pytest.mark.preferences(browser_mode="list")
def test_delete_confirmation_baseline(yata, baseline):
    yata.select_entry_with_keyboard("todo.txt")
    yata.keyboard.press("shift+Delete")
    yata.wait_for_dialog()
    _settle(yata)
    baseline(yata, "delete-confirmation")


def _settle_icons(yata, tmp_path) -> None:
    _settle(yata, ICONS_BASELINE_ENTRIES)
    icons = {
        name: yata.entry(name).find(role="image")
        for name in ICONS_BASELINE_THUMBNAILS
    }
    assert all(icon is not None for icon in icons.values())

    def thumbnails_ready():
        capture = yata.screenshot(tmp_path / "thumbnail-readiness.png")
        with Image.open(capture) as image:
            pixels = image.convert("RGB")
            return all(
                pixels.getpixel(icons[name].screen_bounds().center) == color
                for name, (_, color) in ICONS_BASELINE_THUMBNAILS.items()
            )

    yata.wait(thumbnails_ready, "both image shapes to finish rendering")


def _settle(yata, entries=BASELINE_ENTRIES) -> None:
    """Park the pointer and wait for the listing before capturing."""

    yata.park_pointer()
    yata.wait(
        lambda: yata.entry_names()
        == entries,
        "the fixture listing to be complete",
    )
    yata.settle(yata.pane())
