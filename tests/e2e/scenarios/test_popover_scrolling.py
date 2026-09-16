# SPDX-License-Identifier: MIT
"""Outside wheel ticks dismiss browser panels and only scroll the pointed listing."""

import pytest

from harness.fixtures import FixtureTree

PANELS = [
    pytest.param(
        "Columns",
        "sort",
        marks=pytest.mark.preferences(browser_mode="columns"),
        id="sort-columns",
    ),
    pytest.param(
        "List",
        "appearance",
        marks=pytest.mark.preferences(browser_mode="list"),
        id="appearance-list",
    ),
    pytest.param(
        "Icons",
        "thumbnail",
        marks=pytest.mark.preferences(browser_mode="icons"),
        id="thumbnail-icons",
    ),
]


@pytest.fixture
def fixture_tree():
    files = {f"{index:03}.txt": f"{index}\n" for index in range(200)}
    fixture = FixtureTree.create({"nested": files, **files})
    try:
        yield fixture
    finally:
        fixture.cleanup()


def viewport(yata, directory=None):
    for node in yata.entry_container(directory).ancestors():
        if node.role == "scroll pane":
            return node.screen_bounds()
    raise AssertionError("listing has no scroll viewport")


def open_panel(yata, panel):
    if panel == "sort":
        yata.pointer.click(yata.header_button("Choose sort field"))
        label = "Folders first"
    elif panel == "appearance":
        yata.open_appearance_menu()
        label = "Compact"
    else:
        yata.pointer.click(yata.header_button("Thumbnail size"))
        label = "Small"
    role = "label" if panel == "thumbnail" else "button"
    return yata.wait(
        lambda: yata.window.find(role=role, name=label),
        f"the {panel} panel to open",
    )


@pytest.mark.parametrize("mode,panel", PANELS)
@pytest.mark.parametrize("target", ["listing", "sidebar", "inside"])
def test_panel_wheel_routing(yata, mode, panel, target):
    row = yata.entry("005.txt")
    yata.settle(row)
    before = row.screen_bounds()
    bounds = viewport(yata)
    option = open_panel(yata, panel)
    if target == "listing":
        point = (bounds.center[0], bounds.y + bounds.height * 4 // 5)
    elif target == "sidebar":
        point = yata.sidebar_button("Home").screen_bounds().center
    else:
        point = option.screen_bounds().center
    yata.pointer.scroll(at=point, clicks=1)
    if target == "inside":
        assert yata.window.find(role=option.role, name=option.name) is not None
        assert row.screen_bounds() == before
    else:
        yata.wait(
            lambda: yata.window.find(role=option.role, name=option.name) is None,
            "outside wheel to close the panel",
        )
        if target == "listing":
            yata.wait(
                lambda: row.screen_bounds().y < before.y,
                "the same wheel tick to move the listing",
            )
        else:
            assert row.screen_bounds() == before


@pytest.mark.parametrize("pointed_column", ["parent", "child"])
def test_outside_wheel_only_moves_the_column_under_the_pointer(yata, pointed_column):
    root = yata.fixture.root.name
    yata.open_directory("nested")
    parent_row = yata.entry("005.txt", directory=root)
    child_row = yata.entry("005.txt", directory="nested")
    yata.settle(parent_row)
    yata.settle(child_row)
    parent_before = parent_row.screen_bounds()
    child_before = child_row.screen_bounds()
    option = open_panel(yata, "appearance")
    bounds = viewport(yata, root if pointed_column == "parent" else "nested")
    yata.pointer.scroll(
        at=(bounds.center[0], bounds.y + bounds.height * 4 // 5), clicks=1
    )
    yata.wait(
        lambda: yata.window.find(role=option.role, name=option.name) is None,
        "outside wheel to close the panel",
    )
    if pointed_column == "parent":
        yata.wait(
            lambda: parent_row.screen_bounds().y < parent_before.y, "parent to scroll"
        )
        assert child_row.screen_bounds() == child_before
    else:
        yata.wait(
            lambda: child_row.screen_bounds().y < child_before.y, "child to scroll"
        )
        assert parent_row.screen_bounds() == parent_before
