# SPDX-License-Identifier: MIT
"""Accessibility semantics the rest of the suite — and screen readers — rely on."""

from __future__ import annotations

import pytest

from harness.modes import ALL_MODES

ROOT_ENTRIES = ["archive", "documents", "pictures", "readme.md", "todo.txt"]
FOLDERS = {"archive", "documents", "pictures"}


@pytest.mark.parametrize("mode", ALL_MODES)
def test_listing_names_descriptions_and_selection_semantics(yata, mode):
    root = yata.fixture.root.name
    pane = yata.pane(root)
    assert pane.name == root
    assert pane.description == f"{mode} view"

    container = yata.entry_container(root)
    assert container is not None
    assert container.name == root
    assert container.description == "Files"

    entries = yata.entries(root)
    assert [node.name for node in entries] == ROOT_ENTRIES
    for node in entries:
        expected = "Folder" if node.name in FOLDERS else "File"
        assert node.description == expected, (
            f"{node.name} should be described as a {expected}"
        )
        assert "focusable" in node.states, f"{node.name} should be focusable"

    # GTK 4.14 omits SELECTABLE on unselected rows; exercise SELECTED transitions.
    yata.select_entry("todo.txt", directory=root)
    assert "selected" in yata.entry("todo.txt", directory=root).states
    others = [node for node in yata.entries(root) if node.name != "todo.txt"]
    assert all("selected" not in node.states for node in others)


def test_toolbar_controls_are_named(yata):
    for name in (
        "Search (Ctrl+K)",
        "Appearance",
        "Settings",
        "Close window",
        "Toggle sidebar (Ctrl+B)",
    ):
        assert yata.window.find(name=name) is not None, f"{name!r} is unnamed"


def test_focus_order_reaches_the_files_from_the_header(yata):
    """Tab from the window's first control eventually reaches the listing."""

    yata.keyboard.press("Tab")
    seen = []
    for _ in range(20):
        focused = yata.focused_node()
        if focused is None:
            yata.keyboard.press("Tab")
            continue
        seen.append(f"{focused.role}:{focused.name}")
        if focused.role in ("list", "table") or yata.focused_name() is not None:
            return
        yata.keyboard.press("Tab")
    raise AssertionError(f"Tab never reached the file listing; visited {seen}")
