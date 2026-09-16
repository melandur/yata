# SPDX-License-Identifier: MIT
"""Settings-wide search keeps input focus while navigating and filtering pages."""

import pytest


@pytest.mark.parametrize("width", [1360, 640], ids=["sidebar", "compact-popover"])
def test_settings_search_filters_navigates_and_clears(yata, width):
    bounds = yata.window.screen_bounds()
    yata.keyboard.connection.resize_surface(bounds.width, bounds.height, width, 700)
    yata.wait(lambda: yata.window.screen_bounds().width == width, "resized window")
    settings = yata.window.find(role="button", name="Settings")
    assert settings is not None and settings.activate()
    if width == 640:
        button = yata.wait(
            lambda: yata.window.find(role="button", name="Search settings"),
            "compact settings search",
        )
        yata.pointer.click(button)
    search = yata.wait(
        lambda: yata.window.find(role="text", name="Search settings"),
        "settings search field",
    )
    original = yata.environment.read_preferences()
    yata.pointer.click(search)
    yata.keyboard.type_text("tezt size")
    yata.wait(lambda: search.text == "tezt size", "search retains focus across page changes")
    yata.wait(
        lambda: yata.window.find(role="spin button", name="Text size in pixels"),
        "nearest text-size setting",
    )
    assert yata.window.find(name="Reduce motion") is None
    assert yata.window.find(name="Search themes") is None
    preferences = yata.environment.read_preferences()
    for key in ("folder_peeking", "text_size", "follow_omarchy", "theme"):
        assert preferences.get(key) == original.get(key)

    bounds = yata.window.screen_bounds()
    width = 640 if width == 1360 else 1360
    yata.keyboard.connection.resize_surface(bounds.width, bounds.height, width, 700)
    yata.wait(lambda: yata.window.screen_bounds().width == width, "resize with an active query")
    search = yata.wait(
        lambda: yata.window.find(role="text", name="Search settings"),
        "search follows the responsive navigation",
    )
    yata.wait(lambda: search.has_state("focused"), "search input focus survives resize")
    assert search.text == "tezt size"
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("folder peeking")
    yata.wait(lambda: search.text == "folder peeking", "replace global query")
    yata.wait(lambda: yata.window.find(name="Folder peeking"), "matching General setting")
    assert yata.window.find(name="Single-click file previews") is None

    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("keep arrows")
    yata.wait(lambda: yata.window.find(name="Keep arrows in file list"), "arrow scope setting")
    assert yata.window.find(name="Folder peeking") is None

    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("default directory")
    yata.wait(
        lambda: yata.window.find(role="button", name="Home directory"),
        "startup directory setting",
    )
    assert yata.window.find(name="Keep arrows in file list") is None

    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("unfindablequantumsetting")
    yata.wait(
        lambda: yata.window.find(role="label", name="No settings match your search."),
        "explicit empty results",
    )
    yata.keyboard.press("Escape")
    yata.wait(lambda: search.text == "", "Escape clears the query before closing Settings")
    if width == 640:
        yata.keyboard.press("Escape")
    yata.wait(
        lambda: yata.window.find(name="Single-click file previews"),
        "unfiltered settings restored",
    )
    assert yata.window.find(role="button", name="Close settings") is not None
