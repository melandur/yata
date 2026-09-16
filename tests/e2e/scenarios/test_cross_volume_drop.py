# SPDX-License-Identifier: MIT
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def drop_volume(yata):
    with tempfile.TemporaryDirectory(prefix="strata-drop-volume-", dir="/dev/shm") as directory:
        volume = Path(directory)
        assert volume.stat().st_dev != yata.fixture.path("todo.txt").stat().st_dev
        yata.fixture.path("drop-volume").symlink_to(volume, target_is_directory=True)
        yield volume


@pytest.mark.parametrize("action,tabs", [("Copy", 0), ("Move", 1), ("Cancel", 2)])
@pytest.mark.preferences(cross_volume_drop_strategy="always-ask")
def test_enter_activates_the_focused_cross_volume_choice(yata, drop_volume, action, tabs):
    contents = yata.fixture.path("todo.txt").read_bytes()
    yata.pointer.drag(yata.entry("todo.txt"), yata.entry("drop-volume"))
    yata.wait_for_dialog()
    for _ in range(tabs):
        yata.keyboard.press("shift+Tab")
    yata.wait(lambda: yata.dialog_button(action).has_state("focused"), f"{action} focused")
    yata.keyboard.press("Return")
    yata.wait(lambda: yata.dialog() is None, "the copy-or-move dialog to close")
    source = yata.fixture.path("todo.txt")
    destination = drop_volume / "todo.txt"
    if action == "Cancel":
        assert not destination.exists(), "Cancel must not start a transfer"
        assert source.exists()
    else:
        yata.wait(lambda: destination.exists(), "the destination to be created")
        if action == "Move":
            yata.wait(lambda: not source.exists(), "the source to move")
        else:
            assert source.exists(), "Copy must preserve the source"
        assert destination.read_bytes() == contents


@pytest.mark.preferences(cross_volume_drop_strategy="always-copy")
def test_plain_cross_volume_copy_does_not_prompt_or_remove_source(yata, drop_volume):
    source = yata.fixture.path("todo.txt")
    contents = source.read_bytes()
    yata.pointer.drag(yata.entry("todo.txt"), yata.entry("drop-volume"))
    destination = drop_volume / "todo.txt"
    yata.wait(lambda: destination.exists(), "the cross-device copy")
    assert source.read_bytes() == contents
    assert destination.read_bytes() == contents
    assert yata.dialog() is None
