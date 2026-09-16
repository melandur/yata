# SPDX-License-Identifier: GPL-3.0-or-later
import tomllib
from pathlib import Path

import pytest
from PIL import Image, ImageColor

from harness.fixtures import FixtureTree
from harness.modes import ALL_MODES, SINGLE_PANE_MODES


@pytest.fixture
def fixture_tree():
    fixture = FixtureTree.create({
        "match-note.txt": "root decoy\n",
        "alpha": {"match-note.txt": "alpha source\n"},
        "beta": {"match-note.txt": "beta source\n", "only-match.txt": "beta source\n"},
        "match-note-other.md": "other match\n",
        "destination": {},
        "thumb.txt": "thumbnail search companion",
    })
    Image.new("RGB", (64, 64), (230, 40, 60)).save(fixture.path("beta/thumb.png"))
    try:
        yield fixture
    finally:
        fixture.cleanup()


def result(yata, path):
    for row in yata.window.find_all(role="list item", name=Path(path).name):
        if any(label.name.endswith(path) for label in row.find_all(role="label")):
            return row
    return None


def filter_results(yata, query="match-note", count=4, directory=None):
    yata.select_entry("match-note.txt", directory)
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    yata.keyboard.type_text(query)
    yata.wait(lambda: len(yata.matches()) == count, "all recursive matches")
    return field


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("route", ["shift", "keyboard-range", "select-all", "marquee"])
@pytest.mark.parametrize("recursive", [
    pytest.param(False, marks=pytest.mark.preferences(filter_include_subfolders=False)),
    pytest.param(True, marks=pytest.mark.preferences(filter_include_subfolders=True)),
])
def test_filtered_results_support_group_selection(yata, mode, route, recursive):
    count = 4 if recursive else 2
    filter_results(yata, count=count)
    rows = yata.window.find_all(role="list item")
    rows = [row for row in rows if "match-note" in row.name]
    assert len(rows) == count
    if route == "marquee":
        first = rows[0].screen_bounds()
        last = rows[-1].screen_bounds()
        yata.pointer.drag_points(
            (last.center[0], last.y + last.height + 25),
            (first.x + 15, first.y + 2),
        )
    else:
        yata.pointer.click(rows[0], modifiers=("ctrl",))
        if route == "shift":
            yata.pointer.click(rows[-1], modifiers=("shift",))
        else:
            yata.keyboard.press("ctrl+f")
            yata.keyboard.press("Down")
            if route == "keyboard-range":
                for _ in range(count - 1):
                    yata.keyboard.press("shift+Down")
            else:
                yata.keyboard.press("ctrl+a")
    yata.wait(
        lambda: all(row.has_state("selected") for row in rows),
        "all filtered results to be selected",
    )


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("operation", ["drag", "copy"])
def test_filtered_control_selection_operates_on_the_selected_group(yata, mode, operation):
    filter_results(yata, query="match", count=5)
    first = result(yata, "beta/only-match.txt")
    second = result(yata, "match-note-other.md")
    assert first is not None and second is not None
    yata.pointer.click(first, modifiers=("ctrl",))
    yata.pointer.click(second, modifiers=("ctrl",))
    yata.pointer.click(first, modifiers=("ctrl",))
    yata.wait(lambda: not first.has_state("selected"), "Ctrl-click to deselect a result")
    yata.pointer.click(first, modifiers=("ctrl",))
    yata.wait(
        lambda: first.has_state("selected") and second.has_state("selected"),
        "both filtered files to be selected",
    )
    if operation == "drag":
        yata.pointer.drag(first, yata.sidebar_button("Home"))
    else:
        yata.pointer.right_click(first)
        yata.wait(yata.context_menu, "the selected group menu")
        assert first.has_state("selected") and second.has_state("selected")
        yata.choose_menu_item("Copy")
        yata.keyboard.press("ctrl+l")
        yata.keyboard.press("ctrl+a")
        yata.keyboard.type_text(str(yata.environment.home))
        yata.keyboard.press("Return")
        yata.wait_for_directory(yata.environment.home.name)
        yata.keyboard.press("ctrl+v")
    for path, contents in [("beta/only-match.txt", "beta source\n"),
                           ("match-note-other.md", "other match\n")]:
        destination = yata.environment.home / Path(path).name
        yata.wait(lambda: destination.exists(), "the selected file to arrive in Home")
        assert destination.read_text() == contents
        assert yata.fixture.path(path).exists() == (operation == "copy")
    assert yata.fixture.path("match-note.txt").read_text() == "root decoy\n"


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("shortcut", ["ctrl+c", "ctrl+x"])
@pytest.mark.parametrize("hints", [
    pytest.param(False, marks=pytest.mark.preferences(show_keybinding_hints=False)),
    pytest.param(True, marks=pytest.mark.preferences(show_keybinding_hints=True)),
])
def test_filtered_keyboard_clipboard_keeps_status_visible(yata, mode, shortcut, hints):
    filter_results(yata, query="match", count=5)
    for path in ["beta/only-match.txt", "match-note-other.md"]:
        row = result(yata, path)
        assert row is not None
        yata.pointer.click(row, modifiers=("ctrl",))
    yata.keyboard.press(shortcut)
    yata.wait(
        lambda: yata.window.find(role="label", name="Files on clipboard"),
        "the file clipboard status badge",
    )
    assert bool(yata.window.find(role="button", name="F1  Shortcuts")) == hints
    assert yata.fixture.path("beta/only-match.txt").exists()
    assert yata.fixture.path("match-note-other.md").exists()
    yata.keyboard.press("ctrl+l")
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text(str(yata.fixture.path("destination")))
    yata.keyboard.press("Return")
    yata.wait_for_directory("destination")
    yata.keyboard.press("ctrl+v")
    for path, contents in [("beta/only-match.txt", "beta source\n"),
                           ("match-note-other.md", "other match\n")]:
        destination = yata.fixture.path(f"destination/{Path(path).name}")
        yata.wait(lambda: destination.exists(), "the clipboard file to arrive")
        assert destination.read_text() == contents
        assert yata.fixture.path(path).exists() == (shortcut == "ctrl+c")
    assert yata.fixture.path("match-note.txt").read_text() == "root decoy\n"


@pytest.mark.parametrize("mode", ALL_MODES)
def test_filter_right_arrow_moves_the_text_cursor(yata, mode):
    yata.switch_view(mode)
    field = filter_results(yata)
    yata.keyboard.press("Home")
    yata.keyboard.press("Right")
    yata.keyboard.type_text("X")
    yata.wait(lambda: field.text == "mXatch-note", "Right to move the filter caret")


def test_filter_text_selection_uses_the_active_theme(yata, tmp_path):
    field = filter_results(yata)
    yata.keyboard.press("ctrl+a")
    settings = tomllib.loads(yata.environment.settings_path.read_text())
    catalog = Path(__file__).resolve().parents[3] / "data/themes/catalog.toml"
    themes = tomllib.loads(catalog.read_text())["themes"]
    theme = next(theme for theme in themes if theme["id"] == settings["theme"])
    accent = ImageColor.getrgb(theme["accent"])

    def selected_text_has_theme_background():
        bounds = field.screen_bounds()
        capture = yata.screenshot(tmp_path / "filter-selection.png")
        with Image.open(capture) as image:
            pixels = image.convert("RGB").crop((
                bounds.x + 2, bounds.y + 2,
                bounds.x + bounds.width - 2, bounds.y + bounds.height - 2,
            ))
            return sum(count for count, color in pixels.getcolors(pixels.width * pixels.height)
                       if color == accent) > 100

    yata.wait(selected_text_has_theme_background, "theme-colored filter text selection")


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("trigger,query,count,target", [
    ("pointer", "match-note", 4, "beta/match-note.txt"),
    ("keyboard", "match-note", 4, "beta/match-note.txt"),
    ("keyboard", "only-match", 1, "beta/only-match.txt"),
])
def test_filtered_item_menu_actions_use_the_real_location(yata, mode, trigger, query, count, target):
    directory = "beta" if mode == "Columns" and count == 1 else None
    if directory:
        yata.open_directory(directory)
    field = filter_results(yata, query, count, directory)
    row = yata.wait(lambda: result(yata, target), "the beta result")
    if mode == "Columns" and count == 1:
        yata.hover_pane(yata.fixture.root.name)
    if trigger == "pointer":
        yata.pointer.right_click(row)
        yata.wait(yata.context_menu, "the result menu")
        yata.keyboard.press("Escape")
        yata.wait(lambda: yata.context_menu() is None, "the pointer result menu to close")
        yata.wait(lambda: row.has_state("focused"), "focus to return to the right-clicked result")
        yata.pointer.right_click(row)
    else:
        yata.keyboard.press("Down")
        yata.wait(lambda: not field.has_state("focused"), "Down to leave the filter input")
        for _ in range(count):
            if row.has_state("focused"):
                break
            yata.keyboard.press("Down")
        yata.wait(lambda: row.has_state("focused"), "keyboard focus on the actual result")
        yata.keyboard.press("ctrl+f")
        yata.wait(lambda: field.has_state("focused"), "Ctrl+F to refocus the query")
        assert field.text == query
        yata.keyboard.press("Down")
        yata.wait(lambda: row.has_state("focused"), "Down to resume the selected result")
        for _ in range(count):
            yata.keyboard.press("Up")
            if field.has_state("focused"):
                break
        yata.wait(lambda: field.has_state("focused"), "Up from the first result to the query")
        assert field.text == query
        yata.keyboard.press("Down")
        yata.wait(lambda: not field.has_state("focused"), "Down to reenter results")
        for _ in range(count):
            if row.has_state("focused"):
                break
            yata.keyboard.press("Down")
        yata.wait(lambda: row.has_state("focused"), "keyboard result focus after the round trip")
        yata.keyboard.press("Menu")
        yata.wait(yata.context_menu, "the keyboard result menu")
        yata.keyboard.press("Escape")
        yata.wait(lambda: yata.context_menu() is None, "the result menu to close")
        yata.wait(lambda: row.has_state("focused"), "focus to return to the result")
        yata.keyboard.press("shift+F10")
    yata.wait(yata.context_menu, "the result menu")
    assert row.has_state("selected")
    assert "Quick preview" in yata.menu_items()
    assert "New Folder" not in yata.menu_items()
    if trigger == "keyboard":
        yata.keyboard.press("Home")
        yata.keyboard.press("Up")
        assert not field.has_state("focused")
        yata.keyboard.press("Home")
        for _ in yata.menu_items():
            if yata.menu_item("Properties").has_state("focused"):
                break
            yata.keyboard.press("Down")
        assert yata.menu_item("Properties").has_state("focused")
        yata.keyboard.press("Return")
    else:
        yata.choose_menu_item("Properties")
    dialog = yata.wait_for_dialog()
    assert target in dialog.dump()
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "result Properties to close")
    yata.wait(lambda: row.has_state("focused"), "Properties to restore the actual search result")
    assert row.has_state("selected")
    assert field.text == query
    if trigger == "pointer":
        yata.pointer.right_click(row)
    else:
        yata.keyboard.press("Menu")
    yata.wait(yata.context_menu, "the restored result menu")
    yata.choose_menu_item("Quick preview")
    yata.wait(lambda: yata.preview_shows("beta source"), "preview of the nested result")
    assert field.text == query
    yata.keyboard.press("ctrl+f")
    yata.wait(lambda: field.has_state("focused"), "Ctrl+F to return from the preview")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview() is None, "Space to close preview")
    assert field.text == query
    yata.pointer.right_click(result(yata, target))
    yata.wait(yata.context_menu, "the selected result menu")
    yata.choose_menu_item("Copy")
    assert field.text == query
    yata.keyboard.press("ctrl+l")
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text(str(yata.fixture.path("destination")))
    yata.keyboard.press("Return")
    yata.wait_for_directory("destination")
    yata.keyboard.press("ctrl+v")
    destination = yata.fixture.path(f"destination/{Path(target).name}")
    yata.wait(lambda: destination.exists() and destination.read_text() == "beta source\n",
                "the actual nested file to be copied")
    assert yata.fixture.path("match-note.txt").read_text() == "root decoy\n"
    assert yata.fixture.path("alpha/match-note.txt").read_text() == "alpha source\n"


@pytest.mark.parametrize("mode", ALL_MODES)
def test_query_updates_retain_selection_focus_preview_and_background_menu(yata, mode):
    field = filter_results(yata)
    row = yata.wait(lambda: result(yata, "beta/match-note.txt"), "the beta result")
    yata.pointer.click(row, modifiers=("ctrl",))
    yata.pointer.click(field)
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("beta source"), "the selected preview")
    for query, count in [("match-note.t", 3), ("match-note", 4)] * 2:
        yata.keyboard.press("ctrl+a")
        yata.keyboard.type_text(query)
        yata.wait(lambda: len(yata.matches()) == count, "the updated result count")
        assert result(yata, "beta/match-note.txt").has_state("selected")
        assert field.has_state("focused")
        assert field.text == query
        assert yata.preview_shows("beta source")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview() is None, "Space to close after updates")
    assert field.text == "match-note"
    yata.pointer.right_click(yata.pane(), at=yata.background_point())
    yata.wait(yata.context_menu, "the empty-space menu")
    assert "New Folder" in yata.menu_items()
    assert "Quick preview" not in yata.menu_items()


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("trigger,focus_filter", [
    ("menu", False),
    ("F2", False),
    ("F2", True),
    ("ctrl+r", False),
    ("ctrl+r", True),
])
def test_filtered_rename_targets_the_nested_duplicate(yata, mode, trigger, focus_filter):
    field = filter_results(yata)
    row = yata.wait(lambda: result(yata, "beta/match-note.txt"), "the beta result")
    if trigger == "menu":
        yata.pointer.right_click(row)
        yata.wait(yata.context_menu, "the result menu")
        yata.choose_menu_item("Rename")
    else:
        yata.pointer.click(row, modifiers=("ctrl",))
        if focus_filter:
            yata.pointer.click(field)
        yata.keyboard.press(trigger)
    yata.wait_for_dialog()
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "rename dialog to close")
    yata.wait(
        lambda: result(yata, "beta/match-note.txt").has_state("focused"),
        "focus to return to the originating result",
    )
    assert result(yata, "beta/match-note.txt").has_state("selected")
    assert field.text == "match-note"
    assert yata.fixture.path("beta/match-note.txt").read_text() == "beta source\n"
    assert yata.fixture.path("match-note.txt").read_text() == "root decoy\n"
    yata.keyboard.press("F2")
    yata.wait_for_dialog()
    yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("renamed.txt")
    yata.keyboard.press("Return")
    renamed = yata.fixture.path("beta/renamed.txt")
    yata.wait(lambda: renamed.exists() and renamed.read_text() == "beta source\n", "the nested rename")
    assert not yata.fixture.path("beta/match-note.txt").exists()
    assert yata.fixture.path("alpha/match-note.txt").read_text() == "alpha source\n"
    assert yata.fixture.path("match-note.txt").read_text() == "root decoy\n"
    assert field.text == "match-note"
    yata.wait(lambda: result(yata, "beta/match-note.txt") is None, "the stale hit to disappear")
    yata.pointer.click(field)
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("match-note.t")
    yata.wait(lambda: len(yata.matches()) == 2, "only the surviving matches after a query change")
    assert result(yata, "beta/match-note.txt") is None


@pytest.mark.parametrize("mode", ALL_MODES)
def test_delete_trashes_filtered_result_without_touching_hidden_selection(yata, mode):
    filter_results(yata)
    row = yata.wait(lambda: result(yata, "beta/match-note.txt"), "the beta result")
    yata.pointer.click(row, modifiers=("ctrl",))
    yata.keyboard.press("F2")
    yata.wait_for_dialog()
    yata.keyboard.press("Escape")
    yata.wait(lambda: result(yata, "beta/match-note.txt").has_state("focused"), "result focus")
    yata.keyboard.press("Delete")
    yata.wait(
        lambda: not yata.fixture.path("beta/match-note.txt").exists(),
        "the selected result to be trashed",
    )
    assert yata.fixture.path("match-note.txt").read_text() == "root decoy\n"
    assert yata.fixture.path("alpha/match-note.txt").read_text() == "alpha source\n"


@pytest.mark.parametrize("mode", ALL_MODES)
@pytest.mark.parametrize("query", ["", "no-such-result"])
def test_filter_rename_shortcuts_do_not_target_the_hidden_directory_selection(yata, mode, query):
    yata.select_entry("match-note.txt")
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    if query:
        yata.keyboard.type_text(query)
        yata.wait(lambda: len(yata.matches()) == 0, "no matching results")
        yata.keyboard.press("Down")
        assert field.has_state("focused")
        assert field.text == query
    for shortcut in ["F2", "ctrl+r"]:
        yata.keyboard.press(shortcut)
        yata.settle(field)
        assert yata.dialog() is None
        assert field.has_state("focused")
        assert field.text == query
    assert yata.fixture.path("match-note.txt").read_text() == "root decoy\n"


@pytest.mark.parametrize("mode", SINGLE_PANE_MODES)
def test_filtered_thumbnail_stays_rendered_across_updates(yata, mode, tmp_path):
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    yata.keyboard.type_text("thumb")
    yata.wait(lambda: len(yata.matches()) == 2, "image and text results")
    row = yata.window.find(role="list item", name="thumb.png")
    assert row is not None
    yata.pointer.click(row, modifiers=("ctrl",))
    yata.pointer.click(field)
    icon = row.find(role="image")
    assert icon is not None

    def thumbnail_pixel():
        row_bounds = yata.settle(row).screen_bounds()
        bounds = icon.screen_bounds()
        capture = yata.screenshot(tmp_path / "thumbnail.png")
        with Image.open(capture) as image:
            return image.convert("RGB").getpixel((bounds.center[0], row_bounds.center[1]))

    yata.wait(lambda: thumbnail_pixel() == (230, 40, 60), "the generated red thumbnail")
    for query, count in [("thumb.p", 1), ("thumb", 2)]:
        yata.keyboard.press("ctrl+a")
        yata.keyboard.type_text(query)
        yata.wait(lambda: len(yata.matches()) == count, "updated image results")
        assert row.has_state("selected")
        # AT-SPI result updates can precede the corresponding rendered frame.
        yata.wait(lambda: thumbnail_pixel() == (230, 40, 60), "the updated red thumbnail")
        assert field.has_state("focused")
