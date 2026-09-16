# SPDX-License-Identifier: MIT

import pytest

from harness.artifacts import ArtifactCollector
from harness.modes import ALL_MODES


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("destination", ["Home", "Trash"])
def test_sidebar_destinations_accept_three_files(yata, mode, destination):
    names = [f"drop-{letter}.txt" for letter in "abc"]
    for name in names:
        yata.fixture.path(name).write_text(name)
        yata.entry(name)
    yata.select_entry(names[0])
    for name in names[1:]:
        yata.pointer.click(yata.entry(name), modifiers=["ctrl"])
    yata.wait_for_selection(names)
    target = yata.sidebar_button(destination)
    source = yata.entry(names[0])
    yata.pointer.drag_points(
        yata.pointer.drag_origin(source), target.screen_bounds().center, release=False
    )
    try:
        artifacts = ArtifactCollector(test_name=f"sidebar-drop-{destination}-{mode}")
        yata.screenshot(artifacts.directory / "hover.png")
    finally:
        yata.pointer.connection.button(1, False)
    yata.wait(
        lambda: all(not yata.fixture.path(name).exists() for name in names),
        "all three sources to leave their original directory",
    )
    directory = yata.environment.home if destination == "Home" else yata.environment.trash_files
    yata.wait(
        lambda: all((directory / name).exists() and (directory / name).read_text() == name for name in names),
        "all three files to arrive intact",
    )
    if destination == "Trash":
        yata.keyboard.press("ctrl+z")
        yata.wait(
            lambda: all(yata.fixture.path(name).exists() for name in names),
            "all three trashed files to be restored by undo",
        )
