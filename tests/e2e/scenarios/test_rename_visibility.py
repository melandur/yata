# SPDX-License-Identifier: GPL-3.0-or-later
"""Inline editors and committed names stay inside their listing viewport."""

import pytest


def wait_for_visible_commit(yata, name, mode="Columns"):
    def visible():
        pane = yata.pane("rename-target")
        entry = pane.find(role="list item", name=name)
        footer = pane.find(role="label", name_matches="Paste here")
        if entry is None or (mode == "Columns" and footer is None) or not entry.has_state("selected"):
            return False
        panel = entry.find(role="panel")
        if panel is None:
            return False
        bounds = panel.screen_bounds()
        viewport = yata.entry_container("rename-target").screen_bounds()
        return (
            bounds.width > 0 and bounds.height > 0
            and bounds.x >= viewport.x and bounds.y >= viewport.y
            and bounds.x + bounds.width <= viewport.x + viewport.width
            and bounds.y + bounds.height <= min(
                viewport.y + viewport.height,
                footer.screen_bounds().y if mode == "Columns" else viewport.y + viewport.height
            )
        )

    yata.wait(visible, f"{name} selected and fully inside the viewport")
    yata.settle(yata.entry(name, "rename-target").find(role="panel"))
    assert visible()


def begin_long_directory_rename(yata, kind, new, mode="Columns"):
    yata.switch_view(mode)
    yata.fixture.path("rename-target").mkdir()
    for index in range(80):
        path = yata.fixture.path(f"rename-target/m-entry-{index:03d}")
        if kind == "folder":
            path.mkdir()
            (path / "marker").write_text("body\n")
        else:
            path.write_text("body\n")
    yata.keyboard.press("F5")
    yata.entry("rename-target")
    yata.open_directory("rename-target")
    yata.keyboard.press("Home")
    yata.keyboard.press("End")
    original = "m-entry-079"
    yata.wait_for_selection([original], "rename-target")
    if new:
        # Aim creation at the parent, not the selected folder's child column.
        bounds = yata.entry_container("rename-target").screen_bounds()
        yata.pointer.right_click(
            yata.pane("rename-target"),
            at=(bounds.x + 1, bounds.y + bounds.height // 2),
        )
        yata.choose_menu_item("New File" if kind == "file" else "New Folder")
        original = "new " + kind
        yata.wait(
            yata.fixture.path("rename-target/" + original).exists,
            "the new item on disk",
        )
    else:
        yata.keyboard.press("F2")
    field = yata.editable_field()
    yata.wait(lambda: field.text == original, "the original name in the editor")
    def editor_visible():
        viewport = yata.entry_container("rename-target").screen_bounds()
        footer = yata.pane("rename-target").find(role="label", name_matches="Paste here")
        bounds = field.screen_bounds()
        return (bounds.height > 0 and bounds.width > 0
                and bounds.y >= viewport.y
                and bounds.y + bounds.height <= (footer.screen_bounds().y
                    if mode == "Columns" else viewport.y + viewport.height))

    yata.wait(editor_visible, "the initial editor inside the viewport without scrolling")
    yata.settle(field)
    assert editor_visible()
    path = yata.fixture.path("rename-target/" + original)
    assert path.is_dir() if kind == "folder" else path.is_file()
    return field, original


@pytest.mark.parametrize("new", (False, True), ids=("existing", "new"))
@pytest.mark.parametrize("final_name", ("a-final", "m-entry-078a", "zz-final"))
@pytest.mark.parametrize("mode", ("Columns", "List"))
def test_committed_rename_visibility(yata, new, final_name, mode):
    field, original = begin_long_directory_rename(yata, "file", new, mode)
    yata.keyboard.type_text(final_name)
    yata.wait(lambda: field.text == final_name, "the committed name in the editor")
    yata.keyboard.press("Return")
    destination = yata.fixture.path("rename-target/" + final_name)
    yata.wait(destination.exists, "the renamed item on disk")
    yata.wait_for_entry_gone(original, "rename-target")
    assert destination.read_text() == ("" if new else "body\n")
    assert not yata.fixture.path("rename-target/" + original).exists()
    wait_for_visible_commit(yata, final_name, mode)
    names = sorted(path.name for path in yata.fixture.path("rename-target").iterdir())
    position = names.index(final_name)
    key, neighbor = ("Down", names[position + 1]) if position == 0 else ("Up", names[position - 1])
    yata.keyboard.press(key)
    yata.wait_for_selection([neighbor], "rename-target")
    yata.keyboard.press("Up" if key == "Down" else "Down")
    yata.wait_for_selection([final_name], "rename-target")
    wait_for_visible_commit(yata, final_name, mode)


@pytest.mark.preferences(browser_density="airy")
@pytest.mark.parametrize("mode", ("Columns", "List"))
def test_airy_committed_rename_stays_visible(yata, mode):
    field, original = begin_long_directory_rename(yata, "file", False, mode)
    final_name = "zz-airy-final"
    yata.keyboard.type_text(final_name)
    yata.wait(lambda: field.text == final_name, "the committed name in the editor")
    yata.keyboard.press("Return")
    yata.wait(
        yata.fixture.path("rename-target/" + final_name).exists,
        "the renamed item on disk",
    )
    yata.wait_for_entry_gone(original, "rename-target")
    wait_for_visible_commit(yata, final_name, mode)


@pytest.mark.parametrize("mode", ("Columns", "List"))
def test_already_visible_rename_preserves_scroll(yata, mode):
    begin_long_directory_rename(yata, "file", False, mode)
    yata.keyboard.press("Escape")
    for _ in range(8):
        yata.keyboard.press("Up")
    original = "m-entry-071"
    final_name = original + "a"
    yata.wait_for_selection([original], "rename-target")
    # A preceding row is unaffected by the editor's temporary extra height.
    anchor_name = "m-entry-070"
    anchor = yata.entry(anchor_name, "rename-target").find(role="panel")
    yata.settle(anchor)
    before = anchor.screen_bounds()
    wait_for_visible_commit(yata, original, mode)

    yata.keyboard.press("F2")
    field = yata.editable_field()
    yata.wait(lambda: field.text == original, "the visible row's rename editor")
    yata.settle(field)
    assert anchor.screen_bounds() == before
    yata.keyboard.type_text(final_name)
    yata.wait(lambda: field.text == final_name, "the replacement name")
    yata.keyboard.press("Return")
    destination = yata.fixture.path("rename-target/" + final_name)
    yata.wait(destination.exists, "the visible row renamed on disk")
    yata.wait_for_entry_gone(original, "rename-target")
    assert not yata.fixture.path("rename-target/" + original).exists()
    assert destination.read_text() == "body\n"
    wait_for_visible_commit(yata, final_name, mode)
    anchor = yata.entry(anchor_name, "rename-target").find(role="panel")
    yata.settle(anchor)
    assert anchor.screen_bounds() == before


@pytest.mark.parametrize("mode", ("Columns", "List"))
def test_click_away_rename_respects_navigation(yata, mode):
    field, original = begin_long_directory_rename(yata, "file", False, mode)
    yata.keyboard.type_text("a-final")
    yata.wait(lambda: field.text == "a-final", "the final name in the editor")
    if mode == "Columns":
        # The root column remains visible while the long child column is scrolled.
        yata.pointer.click(yata.entry("documents", yata.fixture.root.name))
    else:
        yata.pointer.click(yata.sidebar_button("Home"))
    destination = yata.fixture.path("rename-target/a-final")
    yata.wait(destination.exists, "the rename on disk")
    if mode == "Columns":
        yata.wait_for_directory("documents")
        yata.wait_for_selection(["documents"], yata.fixture.root.name)
    else:
        yata.wait_for_directory("home")
    assert not yata.fixture.path("rename-target/" + original).exists()
    assert "rename-target" not in yata.pane_names()


@pytest.mark.parametrize("mode", ("Columns", "List"))
def test_already_visible_created_item_preserves_scroll(yata, mode):
    yata.switch_view(mode)
    yata.fixture.path("rename-target").mkdir()
    for name in ["a-anchor"] + [f"z-entry-{index:03d}" for index in range(80)]:
        yata.fixture.path("rename-target/" + name).write_text("body\n")
    yata.keyboard.press("F5")
    yata.entry("rename-target")
    yata.open_directory("rename-target")
    yata.keyboard.press("Home")
    yata.wait_for_selection(["a-anchor"], "rename-target")
    anchor = yata.entry("a-anchor", "rename-target").find(role="panel")
    yata.settle(anchor)
    before = anchor.screen_bounds()
    bounds = yata.entry_container("rename-target").screen_bounds()
    yata.pointer.right_click(yata.pane("rename-target"),
                               at=(bounds.x + 1, bounds.y + bounds.height // 2))
    yata.choose_menu_item("New File")
    field = yata.editable_field()
    original = "new file"
    yata.wait(lambda: field.text == original, "the created item's editor")
    yata.settle(field)
    assert yata.entry("a-anchor", "rename-target").find(role="panel").screen_bounds() == before
    yata.keyboard.type_text(original + " renamed")
    yata.keyboard.press("Return")
    yata.wait(yata.fixture.path("rename-target/" + original + " renamed").exists,
                "the created item renamed on disk")
    wait_for_visible_commit(yata, original + " renamed", mode)
    anchor = yata.entry("a-anchor", "rename-target").find(role="panel")
    yata.settle(anchor)
    assert anchor.screen_bounds() == before
