# SPDX-License-Identifier: MIT
"""Column background clicks focus the parent without closing its descendants."""

import pytest


@pytest.mark.preferences(browser_mode="columns", single_click_previews=False)
@pytest.mark.parametrize("surface", ["item", "background"])
@pytest.mark.parametrize("previous", ["root", "nested"])
def test_context_menu_keeps_the_clicked_column_target(yata, surface, previous):
    root = yata.fixture.root.name
    nested = yata.fixture.path("documents/nested")
    nested.mkdir()
    (nested / "child.txt").write_text("child")
    yata.open_directory("documents")
    yata.open_directory("nested", directory="documents")
    previous_directory = root if previous == "root" else "nested"
    yata.select_entry(
        "readme.md" if previous == "root" else "child.txt",
        directory=previous_directory,
    )
    if surface == "item":
        yata.open_context_menu("notes.txt", directory="documents")
    else:
        yata.pointer.click(
            yata.pane("documents"),
            at=yata.background_point("documents"),
            button=3,
        )
        yata.wait(yata.context_menu, "the background context menu to open")

    def action_owners():
        return [name for name in yata.pane_names()
                if yata.pane(name).find(role="button", name="Refresh (F5)") is not None]

    yata.wait(lambda: action_owners() == ["documents"], "actions to stay on the menu's column")
    yata.pointer.move_to(*yata.pane(previous_directory).screen_bounds().center)
    assert yata.context_menu() is not None
    assert action_owners() == ["documents"]
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.context_menu() is None, "the context menu to close")
    yata.keyboard.press("Down")
    yata.wait_for_focused_entry("report.md" if surface == "item" else "notes.txt")
    yata.wait(lambda: action_owners() == ["documents"], "keyboard navigation to resume in the menu's column")


@pytest.mark.preferences(browser_mode="columns")
@pytest.mark.parametrize("surface", ["content", "header"])
def test_column_background_click_focuses_parent(yata, surface):
    root = yata.fixture.root.name
    yata.open_directory("documents")
    selected = yata.selected_names(directory=root)
    if surface == "content":
        yata.pointer.click(yata.pane(root), at=yata.background_point(root))
    else:
        heading = yata.window.find(
            role="label", name=root, description=str(yata.fixture.root)
        )
        assert heading is not None
        yata.pointer.click(heading)
    yata.wait_for_directory(root)
    if surface == "content":
        yata.wait_for_selection(["archive"], root)
        yata.pointer.click(yata.pane(root), at=yata.background_point(root))
        yata.wait(lambda: not yata.all_selected_names(), "active background click to clear selection")
    else:
        assert yata.selected_names(directory=root) == selected
    assert "documents" in yata.pane_names()
