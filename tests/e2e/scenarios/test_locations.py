# SPDX-License-Identifier: MIT
"""Opening locations directly and reacting to filesystem changes."""

from __future__ import annotations

import pytest

from harness.modes import COLUMNS_AND_ONE


def test_typing_a_path_navigates_there(yata):
    yata.keyboard.press("ctrl+l")
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text(str(yata.fixture.path("documents")))
    yata.wait(
        lambda: field.text.endswith("documents"),
        "the path to be typed into the address bar",
    )
    yata.keyboard.press("Return")

    yata.wait_for_directory("documents")
    yata.entry("notes.txt", directory="documents")


def test_a_breadcrumb_returns_to_the_parent(yata):
    yata.open_directory("documents")

    crumb = yata.wait(
        lambda: yata.window.find(role="button", name=yata.fixture.root.name),
        "the breadcrumb for the fixture root",
    )
    yata.pointer.click(crumb)

    yata.wait_for_directory(yata.fixture.root.name)


def test_current_breadcrumb_opens_hierarchy_instead_of_window_menu(yata):
    path = yata.fixture.root
    for index in range(6):
        path = path / f"deep-breadcrumb-component-{index}"
    path.mkdir(parents=True)
    yata.entry("deep-breadcrumb-component-0")
    yata.keyboard.press("ctrl+l")
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text(str(path))
    yata.wait(lambda: field.text == str(path), "typed location")
    yata.keyboard.press("Return")
    yata.wait_for_directory(path.name)
    label = yata.wait(
        lambda: yata.window.find(role="label", name=path.name),
        "current breadcrumb",
    )
    yata.pointer.click(label, button=3)
    yata.wait(
        lambda: yata.window.find(role="button", name=path.name),
        "current hierarchy item",
    )
    item = yata.window.find_all(role="button", name=path.parent.name)[-1]
    yata.pointer.click(item)
    yata.wait_for_directory(path.parent.name)


def test_a_sidebar_place_navigates_there(yata):
    home = yata.environment.home
    (home / "sidebar-target.txt").write_text("target\n")

    yata.pointer.click(yata.sidebar_button("Home"))

    yata.wait_for_directory(home.name)
    yata.entry("sidebar-target.txt")


@pytest.mark.parametrize("mode", COLUMNS_AND_ONE)
def test_refresh_reconciles_external_file_creation_and_removal(yata, mode):
    yata.entry("todo.txt")
    yata.fixture.path("appeared-later.txt").write_text("new\n")
    yata.fixture.path("todo.txt").unlink()

    yata.keyboard.press("F5")

    yata.entry("appeared-later.txt")
    yata.wait_for_entry_gone("todo.txt")


def test_an_unreadable_location_reports_an_error(yata):
    blocked = yata.fixture.path("blocked")
    blocked.mkdir()
    blocked.chmod(0o000)
    try:
        yata.keyboard.press("F5")
        yata.select_entry("blocked")

        dialog = yata.wait_for_dialog()
        assert dialog.name == "Unable to open directory", (
            f"unexpected dialog {dialog.name!r}"
        )
        assert any(
            "do not have permission" in node.name
            for node in dialog.find_all(role="label")
        ), f"the dialog should give the reason\n{dialog.dump()}"

        yata.pointer.click(yata.dialog_button("Close"))
        yata.wait(lambda: yata.dialog() is None, "the dialog to close")
    finally:
        blocked.chmod(0o755)
