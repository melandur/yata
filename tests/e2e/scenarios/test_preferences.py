# SPDX-License-Identifier: MIT
"""Saved preferences and live controls share one application-wide state."""

import subprocess

import pytest

from harness.application import binary_path
from harness.environment import process_environment


def _switch(window, name):
    return next(
        (
            node
            for node in window.find_all(name=name, rendered=False)
            if node.role in {"check box", "toggle button", "switch"}
        ),
        None,
    )


def _open_settings(yata, window):
    button = window.find(role="button", name="Settings")
    assert button is not None and button.activate()
    yata.wait(lambda: _switch(window, "Folder peeking"), "General settings to exist")


@pytest.mark.preferences(
    folder_peeking=False, type_to_search=False, single_click_previews=False,
    filter_include_subfolders=False, open_folder_after_drop=False,
)
def test_preferences_sync_across_windows_and_restart(yata):
    variables = process_environment()
    variables.update(yata.environment.variables())
    variables.update(yata.display.environment)
    subprocess.run(
        [str(binary_path()), str(yata.fixture.root)],
        env=variables,
        cwd=yata.fixture.root,
        check=True,
        timeout=30,
        capture_output=True,
    )
    windows = yata.wait(
        lambda: (
            frames
            if len(frames := yata.application.application_node.find_all(
                role="frame", name="yata"
            )) == 2
            else None
        ),
        "two windows in the same yata application",
    )
    for window in windows:
        _open_settings(yata, window)
    for label, key in [
        ("Folder peeking", "folder_peeking"),
        ("Type to search", "type_to_search"),
        ("Single-click file previews", "single_click_previews"),
        ("Include subfolders", "filter_include_subfolders"),
        ("Open folder after dropping files", "open_folder_after_drop"),
    ]:
        switches = [_switch(window, label) for window in windows]
        assert all(not toggle.has_state("checked") for toggle in switches)
        assert switches[0].activate()
        yata.wait(
            lambda: all(toggle.has_state("checked") for toggle in switches),
            f"{label} to enable in both windows",
        )
        assert switches[1].activate()
        yata.wait(
            lambda: all(not toggle.has_state("checked") for toggle in switches),
            f"{label} to disable in both windows",
        )
        yata.wait(
            lambda: yata.environment.read_preferences().get(key) == "false",
            f"{label} to be saved",
        )
    yata.application.stop()
    yata.application.start()
    _open_settings(yata, yata.window)
    for label in [
        "Folder peeking", "Type to search", "Single-click file previews",
        "Include subfolders", "Open folder after dropping files",
    ]:
        assert not _switch(yata.window, label).has_state("checked")
