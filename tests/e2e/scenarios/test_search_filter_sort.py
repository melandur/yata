# SPDX-License-Identifier: MIT
"""Type-to-search, pane filtering, sorting, and hidden files."""

from __future__ import annotations

import pytest

from harness.modes import ALL_MODES, COLUMNS_AND_ONE

ROOT_ENTRIES = ["archive", "documents", "pictures", "readme.md", "todo.txt"]
# Folders stay grouped first, so descending is not simply the reverse.
ROOT_ENTRIES_DESCENDING = ["pictures", "documents", "archive", "todo.txt", "readme.md"]
DOUBLE_CLICK_PREFERENCES = {
    "list_folder_clicks": 2,
    "list_file_clicks": 2,
    "grid_folder_clicks": 2,
    "grid_file_clicks": 2,
    "explorer_folder_clicks": 2,
    "explorer_file_clicks": 2,
    "single_click_previews": True,
}
DOUBLE_CLICK = pytest.mark.preferences(**DOUBLE_CLICK_PREFERENCES)


@pytest.fixture
def launch_counter(test_environment):
    applications = test_environment.data_home / "applications"
    applications.mkdir()
    launches = test_environment.root / "filtered-launches"
    launcher = test_environment.root / "record-filtered-launch"
    launcher.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" >> "{launches}"\n')
    launcher.chmod(0o755)
    (applications / "strata-filtered.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Filtered Result Viewer\n"
        f"Exec={launcher} %U\nMimeType=text/csv;\nNoDisplay=true\n"
    )
    (test_environment.config_home / "mimeapps.list").write_text(
        "[Default Applications]\ntext/csv=strata-filtered.desktop;\n"
        "[Added Associations]\ntext/csv=strata-filtered.desktop;\n"
    )
    return launches


@pytest.fixture
def root(yata) -> str:
    return yata.fixture.root.name


@pytest.mark.parametrize("mode", ALL_MODES)
def test_type_to_search_finds_matches_anywhere_in_the_tree(yata, mode, root):
    yata.select_entry("readme.md", directory=root)

    yata.keyboard.type_text("photo")

    field = yata.editable_field()
    yata.wait(lambda: field.text == "photo", "the typed query to reach the search box")
    yata.wait(
        lambda: yata.matches(root) == ["photo.txt"],
        "the search to list the nested match",
    )

    yata.keyboard.press("Escape")
    yata.wait(
        lambda: yata.entry_names(root) == ROOT_ENTRIES,
        "Escape to restore the directory listing",
    )


@pytest.mark.parametrize("mode", ALL_MODES)
def test_filtering_a_pane_narrows_the_listing(yata, mode, root):
    yata.select_entry("readme.md", directory=root)

    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    yata.keyboard.type_text("spreadsheet")
    yata.wait(lambda: field.text == "spreadsheet", "the filter query to be typed")

    yata.wait(
        lambda: yata.matches(root) == ["spreadsheet.csv"],
        "the filter to list only matching entries",
    )

    yata.keyboard.press("Escape")
    yata.wait(
        lambda: yata.entry_names(root) == ROOT_ENTRIES,
        "Escape to restore the full listing",
    )


@pytest.fixture
def pattern_files(fixture_tree):
    photos = fixture_tree.path("Photos")
    photos.mkdir()
    (photos / "album.MOV").mkdir()
    for name in [
        "clip.MOV", "IMG_001.MOV", "IMG_001.jpg", "clip.MOV.bak", ".hidden.MOV",
        "album.MOV/deep.MOV", "album.MOV/unrelated.txt",
    ]:
        (photos / name).write_text("fixture\n")


@pytest.mark.parametrize("preferences", [
    {"filter_include_subfolders": False},
    {"filter_include_subfolders": True},
], ids=["directory", "subfolders"])
@pytest.mark.parametrize("mode", ALL_MODES)
def test_wildcard_filter_patterns_preserve_scope_and_clear(
    pattern_files, yata, mode, preferences,
):
    yata.open_directory("Photos")
    yata.select_entry("clip.MOV.bak", directory="Photos")
    original = {"album.MOV", "clip.MOV", "IMG_001.MOV", "IMG_001.jpg", "clip.MOV.bak"}
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    recursive = preferences["filter_include_subfolders"]
    for query, expected in [
        ("*.MOV", {"album.MOV", "clip.MOV", "IMG_001.MOV"} | ({"deep.MOV"} if recursive else set())),
        ("IMG*", {"IMG_001.MOV", "IMG_001.jpg"}),
        ("IMG*.MOV", {"IMG_001.MOV"}),
        ("IMG*_001*.mov", {"IMG_001.MOV"}),
        ("*.MOV.b", set()),
        ("*.MOV.b*", {"clip.MOV.bak"}),
        ("*.MOV.b", set()),
        (".MOV.b", {"clip.MOV.bak"}),
        ("*", original | ({"deep.MOV", "unrelated.txt"} if recursive else set())),
    ]:
        yata.keyboard.press("ctrl+a")
        yata.keyboard.type_text(query)
        yata.wait(lambda: field.text == query, "the wildcard query to be typed")
        yata.wait(
            lambda: set(yata.matches("Photos")) == expected,
            f"wildcard results for {query} (subfolders={recursive})",
        )
    yata.keyboard.press("ctrl+a")
    yata.keyboard.press("BackSpace")
    yata.wait(lambda: field.text == "", "the query to clear")
    yata.wait(
        lambda: set(yata.entry_names("Photos")) == original,
        "clearing the wildcard to restore the listing without hidden or nested entries",
    )


def assert_filtered_result_opens(yata):
    yata.select_entry("documents")
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    yata.keyboard.type_text("doc*ments")
    yata.wait(lambda: field.text == "doc*ments", "the filter query")
    result = yata.wait(
        lambda: yata.window.find(role="list item", name="documents"),
        "the filtered folder result",
    )
    yata.pointer.click(result)
    yata.wait_for_directory("documents")


@pytest.mark.preferences(
    **DOUBLE_CLICK_PREFERENCES, filter_include_subfolders=False
)
@pytest.mark.parametrize("mode", COLUMNS_AND_ONE)
def test_local_filtered_results_open_with_one_activation(yata, mode):
    assert_filtered_result_opens(yata)


@DOUBLE_CLICK
@pytest.mark.parametrize("mode", COLUMNS_AND_ONE)
def test_recursive_filtered_results_open_with_one_activation(yata, mode):
    assert_filtered_result_opens(yata)


@DOUBLE_CLICK
@pytest.mark.preferences(browser_mode="list")
def test_recursive_file_double_click_launches_once(launch_counter, yata):
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    yata.keyboard.type_text("spreadsheet")
    result = yata.wait(
        lambda: yata.window.find(role="list item", name="spreadsheet.csv"),
        "the recursive file result",
    )

    yata.pointer.double_click(result)
    yata.wait(
        lambda: launch_counter.exists() and len(launch_counter.read_text().splitlines()) >= 1,
        "the file launch",
    )
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("photo")
    yata.wait(lambda: field.text == "photo", "the follow-up query")
    yata.wait(
        lambda: yata.window.find(role="list item", name="photo.txt") is not None,
        "the follow-up results",
    )
    assert len(launch_counter.read_text().splitlines()) == 1


@pytest.mark.parametrize("mode", ALL_MODES)
def test_filtered_result_waits_for_release_before_launching(launch_counter, yata, mode):
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    yata.keyboard.type_text("spreadsheet")
    yata.wait(lambda: field.text == "spreadsheet", "the filter query")
    result = yata.wait(
        lambda: yata.window.find(role="list item", name="spreadsheet.csv"),
        "the filtered file result",
    )

    def assert_not_launched_on_press():
        assert not launch_counter.exists(), "a held press must not launch the file"

    start = yata.pointer.drag_origin(result)
    end = (start[0] + 40, start[1] + 40)
    yata.pointer.drag_points(
        start, end, release=False, after_press=assert_not_launched_on_press
    )
    try:
        assert not launch_counter.exists(), "crossing the drag threshold must not launch the file"
    finally:
        yata.pointer.connection.button(1, False)


@pytest.mark.preferences(filter_include_subfolders=False)
@pytest.mark.parametrize("mode", ALL_MODES)
def test_directory_only_filter_matches_immediate_files_and_folders(yata, mode, root):
    yata.select_entry("readme.md", directory=root)
    yata.keyboard.press("ctrl+f")
    field = yata.editable_field()
    for query, expected in [
        ("txt", ["todo.txt"]),
        ("photo", []),
        ("archive", ["archive"]),
    ]:
        yata.keyboard.press("ctrl+a")
        yata.keyboard.type_text(query)
        yata.wait(lambda: field.text == query, "the filter query to be typed")
        yata.wait(
            lambda: yata.matches(root) == expected,
            f"directory-only matches for {query}",
        )
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.entry_names(root) == ROOT_ENTRIES, "the listing to return")


def test_dismissing_a_filter_keeps_hidden_files_hidden(yata, root):
    """A cleared query must not also clear the dotfile filter."""

    assert ".hidden.txt" not in yata.entry_names(root)

    yata.select_entry("readme.md", directory=root)
    yata.keyboard.press("ctrl+f")
    yata.editable_field()
    yata.keyboard.type_text("readme")
    yata.wait(
        lambda: yata.matches(root) == ["readme.md"],
        "the filter to narrow the listing",
    )
    yata.keyboard.press("Escape")

    yata.wait(
        lambda: yata.entry_names(root) == ROOT_ENTRIES,
        "the listing to come back without hidden files",
    )


def test_hidden_files_toggle(yata, root):
    assert ".hidden.txt" not in yata.entry_names(root)

    yata.keyboard.press("ctrl+h")

    yata.wait(
        lambda: ".hidden.txt" in yata.entry_names(root),
        "Ctrl+H to reveal hidden files",
    )

    yata.keyboard.press("ctrl+h")
    yata.wait(
        lambda: ".hidden.txt" not in yata.entry_names(root),
        "Ctrl+H to hide them again",
    )


def test_reversing_the_sort_direction(yata, root):
    assert yata.entry_names(root) == ROOT_ENTRIES

    yata.pointer.click(yata.header_button("Ascending — click to reverse"))

    yata.wait(
        lambda: yata.entry_names(root) == ROOT_ENTRIES_DESCENDING,
        "the pane to sort descending with folders still grouped first",
    )

    yata.pointer.click(yata.header_button("Descending — click to reverse"))
    yata.wait(
        lambda: yata.entry_names(root) == ROOT_ENTRIES,
        "the pane to sort ascending again",
    )


def test_sorting_by_size_reorders_the_files(yata, root):
    yata.pointer.click(yata.header_button("Choose sort field"))
    yata.pointer.click(
        yata.wait(
            lambda: yata.window.find(role="button", name="Size"),
            "the Size sort option",
        )
    )

    yata.wait(
        lambda: yata.entry_names(root)[-2:] == ["todo.txt", "readme.md"],
        "the files to be ordered by size",
    )


def test_global_search_arrows_keep_typing_in_the_query_and_enter_opens_selection(yata):
    names = [
        "navigation-alpha",
        "navigation-beta",
        "navigation-final",
        "navigation-gamma",
    ]
    for name in names:
        (yata.environment.home / name).mkdir()

    yata.keyboard.press("ctrl+k")
    field = yata.editable_field()
    yata.keyboard.type_text("nav")
    yata.wait(lambda: field.text == "nav", "the initial global-search query")
    yata.wait(
        lambda: all(
            yata.window.find(role="label", name=name) is not None for name in names
        ),
        "all navigation results to be indexed",
    )

    results = [
        node
        for node in yata.window.find_all(role="list item")
        if any(node.name.endswith(f"/{name}") for name in names)
    ]
    assert len(results) == len(names)
    assert results[0].has_state("selected")
    yata.keyboard.press("Down")
    yata.wait(
        lambda: results[1].has_state("selected"),
        "the first Down press to advance past the preselected result",
    )
    for _ in range(2):
        yata.keyboard.press("Down")
    yata.keyboard.type_text("igation-final")
    yata.wait(
        lambda: field.text == "navigation-final",
        "typing after arrow navigation to extend the query",
    )
    result = yata.wait(
        lambda: next(
            (
                node
                for node in yata.window.find_all(role="list item")
                if node.name.endswith("/navigation-final")
            ),
            None,
        ),
        "the refined selected result",
    )
    yata.wait(
        lambda: result.has_state("selected"),
        "the refined result to be selected",
    )
    yata.keyboard.press("Return")
    yata.wait_for_directory("navigation-final")


@pytest.mark.preferences(search_open_files_directly=False)
def test_global_search_preview_follows_neighbor_when_same_folder_result_is_deleted(yata):
    folder = yata.environment.home / "preview-deletion"
    folder.mkdir()
    previewed = folder / "preview-deletion-fixture.txt"
    previewed.write_text("search preview deletion fixture\n")
    (folder / "remaining.txt").write_text("remaining file\n")
    yata.keyboard.press("ctrl+l")
    yata.keyboard.type_text(str(folder))
    yata.keyboard.press("Return")
    yata.wait_for_directory(folder.name)
    yata.wait(lambda: "remaining.txt" in yata.entry_names(), "loaded folder")
    yata.keyboard.press("ctrl+k")
    yata.keyboard.type_text("preview-deletion-fixture")
    yata.wait(
        lambda: yata.window.find(role="label", name=previewed.name) is not None,
        "indexed search result",
    )
    yata.keyboard.press("Return")
    yata.wait(
        lambda: yata.preview_shows("search preview deletion fixture"),
        "search result preview",
    )
    previewed.unlink()
    yata.wait(
        lambda: yata.preview_shows("remaining file"),
        "deleted result preview to follow the remaining file",
    )
    assert "remaining.txt" in yata.entry_names()


def test_global_search_finds_a_file_under_home(yata, root):
    """Ctrl+K searches the home directory, not the browsed location."""

    nested = yata.environment.home / "reports" / "quarterly-summary.txt"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("summary\n")

    yata.keyboard.press("ctrl+k")
    field = yata.editable_field()
    yata.keyboard.type_text("quarterly")
    yata.wait(lambda: field.text == "quarterly", "the query to be typed")

    yata.wait(
        lambda: any(
            node.name == "quarterly-summary.txt"
            for node in yata.window.find_all(role="label")
        ),
        "the file under home to appear in the search results",
    )

    yata.keyboard.press("Escape")
    yata.wait(
        lambda: yata.window.find(role="text", states={"editable"}) is None,
        "Escape to close the search palette",
    )
