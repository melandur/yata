# SPDX-License-Identifier: MIT
"""Custom typography remains editable and usable across browser presentations."""

import pytest

from harness.artifacts import ArtifactCollector


@pytest.mark.preferences(text_size=17)
def test_settings_text_size_keeps_switches_inside_the_page(yata, request):
    settings = yata.window.find(role="button", name="Settings")
    assert settings is not None and settings.activate()
    for pixels, next_pixels, width in [(17, 11, 1000), (11, 32, 1000), (32, None, 640)]:
        bounds = yata.window.screen_bounds()
        yata.keyboard.connection.resize_surface(bounds.width, bounds.height, width, 600)
        yata.wait(lambda: yata.window.screen_bounds().width == width, "resized settings window")
        general = yata.wait(
            lambda: yata.window.find(role="button", name="General"),
            "General settings navigation",
        )
        assert general.activate()
        toggle = yata.wait(
            lambda: next(
                (node for node in yata.window.find_all(name="Folder peeking")
                 if node.role in {"check box", "toggle button", "switch"}),
                None,
            ),
            "visible folder-peeking switch",
        )
        toggle = _reveal_page_control(yata, "Folder peeking", role=toggle.role)
        scroll = next(node for node in toggle.ancestors() if node.role == "scroll pane")
        bounds, viewport = toggle.screen_bounds(), scroll.screen_bounds()
        assert viewport.x <= bounds.x
        assert bounds.x + bounds.width <= viewport.x + viewport.width
        was_checked = toggle.has_state("checked")
        yata.pointer.click(toggle)
        yata.wait(lambda: toggle.has_state("checked") != was_checked, "resized switch responds to pointer")
        yata.pointer.click(toggle)
        yata.wait(lambda: toggle.has_state("checked") == was_checked, "restore folder peeking")
        if request.config.getoption("--keep-artifacts"):
            yata.screenshot(
                ArtifactCollector(test_name=f"settings-text-size-{pixels}").directory
                / "general.png"
            )
        _reveal_page_control(yata, "Complete setup")
        if request.config.getoption("--keep-artifacts"):
            yata.screenshot(
                ArtifactCollector(test_name=f"settings-text-size-{pixels}").directory
                / "desktop-integration.png"
            )
        theme = yata.window.find(role="button", name="Appearance settings")
        assert theme is not None and theme.activate()
        control = yata.wait(
            lambda: yata.window.find(role="spin button", name="Text size in pixels", rendered=False),
            "numeric text-size control",
        )
        control = _reveal_page_control(yata, "Text size in pixels", role="spin button")
        yata.wait(lambda: _inside_scroll_view(control), "text-size control scrolled into view")
        # GTK exposes the spin button as one accessible value, not separate buttons.
        for fraction, expected in [(1, pixels - 1), (7, pixels)]:
            bounds = control.screen_bounds()
            yata.pointer.click(
                control,
                at=(bounds.x + bounds.width * fraction // 8, bounds.y + bounds.height // 2),
            )
            yata.wait(
                lambda: yata.environment.read_preferences().get("text_size")
                == str(expected),
                "left decrement and right increment buttons",
            )
        if request.config.getoption("--keep-artifacts"):
            yata.screenshot(
                ArtifactCollector(test_name=f"settings-text-size-{pixels}").directory
                / "selector.png"
            )
        if next_pixels is not None:
            yata.pointer.click(control)
            yata.keyboard.press("ctrl+a")
            yata.keyboard.type_text(str(next_pixels))
            yata.keyboard.press("Return")
            yata.wait(
                lambda: yata.environment.read_preferences().get("text_size")
                == str(next_pixels),
                "updated settings text",
            )
        else:
            yata.keyboard.press("ctrl+0")
            yata.wait(
                lambda: yata.environment.read_preferences().get("text_size") == "13",
                "Reset to restore the default text size",
            )
    updates = yata.window.find(role="button", name="Updates")
    assert updates is not None and updates.activate()
    _reveal_page_control(yata, "Check now")
    if request.config.getoption("--keep-artifacts"):
        yata.screenshot(
            ArtifactCollector(test_name="settings-updates").directory / "check-now.png"
        )


def _reveal_page_control(yata, name, role="button"):
    node = yata.wait(lambda: yata.window.find(role=role, name=name, rendered=False), f"{name} control")
    scroll = next(parent for parent in node.ancestors() if parent.role == "scroll pane")

    def revealed():
        if _inside_scroll_view(node):
            return True
        viewport = scroll.screen_bounds()
        # Stay in the content gutter: the scrollbar scrolls by whole pages,
        # which can jump over a control without ever showing all of it.
        # The nested theme library ends before this gutter.
        at = (viewport.x + viewport.width - 16, viewport.y + viewport.height // 2)
        bounds = node.screen_bounds()
        below = bounds.y + bounds.height - (viewport.y + viewport.height)
        above = viewport.y - bounds.y
        # Large text makes General several viewports tall. Traverse distant
        # sections faster, then use single notches so we cannot skip the control.
        clicks = 3 if max(below, above) > viewport.height else 1
        yata.pointer.scroll(at, clicks=clicks, down=below > 0)
        return False

    yata.wait(revealed, f"reachable {name} control")
    return yata.settle(node)


def _inside_scroll_view(node):
    scroll = next(parent for parent in node.ancestors() if parent.role == "scroll pane")
    bounds, viewport = node.screen_bounds(), scroll.screen_bounds()
    return (
        bounds.width > 0
        and bounds.height > 0
        and viewport.x <= bounds.x
        and viewport.y <= bounds.y
        and bounds.x + bounds.width <= viewport.x + viewport.width
        and bounds.y + bounds.height <= viewport.y + viewport.height
    )


@pytest.mark.preferences(text_size=24)
def test_custom_text_size_shortcuts_numeric_control_and_restart(yata, request):
    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+=")
    yata.wait(
        lambda: yata.environment.read_preferences().get("text_size") == "25",
        "zoom in to persist a numeric size",
    )
    yata.keyboard.press("ctrl+-")
    yata.wait(
        lambda: yata.environment.read_preferences().get("text_size") == "24",
        "zoom out to restore the custom size",
    )
    yata.keyboard.press("ctrl+0")
    yata.wait(
        lambda: yata.environment.read_preferences().get("text_size") == "13",
        "reset to the default size",
    )
    if request.config.getoption("--keep-artifacts"):
        yata.screenshot(ArtifactCollector(test_name="text-size").directory / "before.png")
    yata.open_appearance_menu()
    for name, pixels in [
        ("Increase text size (Ctrl++)", "14"),
        ("Decrease text size (Ctrl+−)", "13"),
        ("Decrease text size (Ctrl+−)", "12"),
        ("12 px", "13"),
    ]:
        button = yata.wait(
            lambda: yata.window.find(role="button", name=name),
            f"appearance text-size control {name}",
        )
        yata.pointer.click(button)
        yata.wait(
            lambda: yata.environment.read_preferences().get("text_size") == pixels,
            f"appearance text-size control to persist {pixels}px",
        )
    if request.config.getoption("--keep-artifacts"):
        yata.screenshot(
            ArtifactCollector(test_name="text-size").directory / "appearance.png"
        )
    yata.keyboard.press("Escape")
    yata.keyboard.press("F2")
    rename = yata.wait(
        lambda: yata.window.find(role="text", name="Rename"), "inline rename editor"
    )
    yata.keyboard.press("ctrl+=")
    yata.wait(
        lambda: yata.environment.read_preferences().get("text_size") == "14",
        "zoom while renaming without submitting the editor",
    )
    assert rename.alive
    yata.keyboard.press("Escape")
    assert yata.fixture.path("todo.txt").exists()

    settings = yata.window.find(role="button", name="Settings")
    assert settings is not None and settings.activate()
    theme = yata.wait(
        lambda: yata.window.find(role="button", name="Appearance settings"),
        "appearance settings",
    )
    assert theme.activate()
    control = yata.wait(
        lambda: yata.window.find(role="spin button", name="Text size in pixels", rendered=False),
        "numeric text size control",
    )
    control = _reveal_page_control(yata, "Text size in pixels", role="spin button")
    yata.pointer.click(control)
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("27")
    yata.keyboard.press("Return")
    yata.wait(
        lambda: yata.environment.read_preferences().get("text_size") == "27",
        "an arbitrary typed text size to persist",
    )
    yata.application.stop()
    yata.application.start()
    assert yata.environment.read_preferences()["text_size"] == "27"
    yata.select_entry("todo.txt")
    yata.keyboard.press("ctrl+=")
    yata.wait(
        lambda: yata.environment.read_preferences().get("text_size") == "28",
        "restart to load the exact custom size",
    )
    if request.config.getoption("--keep-artifacts"):
        yata.screenshot(ArtifactCollector(test_name="text-size").directory / "after.png")
