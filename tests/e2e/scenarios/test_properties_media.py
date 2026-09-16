# SPDX-License-Identifier: MIT
"""Properties inspects original media without starting preview playback."""

import subprocess

import pytest
from PIL import Image


def _media_fixture(tree):
    Image.new("RGB", (1600, 900), "green").save(tree.path("photo.png"))
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x180:r=24:d=2",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2",
            "-c:v", "libx264", "-c:a", "aac", "-ac", "2", "-shortest",
            str(tree.path("clip.mp4")),
        ],
        check=True,
        timeout=30,
    )
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:sample_rate=44100:duration=3",
            "-c:a", "pcm_s16le", str(tree.path("sound.wav")),
        ],
        check=True,
        timeout=30,
    )
    tree.path("broken.mp4").write_bytes(b"not a media container")


@pytest.fixture
def fixture_tree(fixture_tree):
    _media_fixture(fixture_tree)
    return fixture_tree


@pytest.mark.parametrize(
    "name, expected, absent",
    [
        ("photo.png", ["1600 × 900 pixels"], ["DURATION", "FRAME RATE", "AUDIO CODEC"]),
        (
            "clip.mp4",
            ["320 × 180 pixels", "0:00:02", "h264", "24.00 fps", "aac", "48.0 kHz", "2 (Stereo)", "BITRATE"],
            [],
        ),
        ("sound.wav", ["0:00:03", "pcm_s16le", "44.1 kHz", "1 (Mono)", "BITRATE"], ["RESOLUTION", "VIDEO CODEC"]),
        ("broken.mp4", ["Unavailable"], ["RESOLUTION", "DURATION"]),
    ],
)
def test_properties_reports_available_media_metadata(yata, fixture_tree, name, expected, absent):
    yata.open_context_menu(name)
    yata.choose_menu_item("Properties")
    dialog = yata.wait_for_dialog()
    for value in expected:
        yata.wait(
            lambda: dialog.find(role="label", name=value, rendered=False),
            f"Properties to report {value} for {name}",
        )
    for value in absent:
        assert dialog.find(role="label", name=value, rendered=False) is None
    if name == "clip.mp4":
        scroll = dialog.find(role="scroll pane")
        executable = dialog.find(name="Allow executing file as a program (+x)", rendered=False)
        assert scroll and executable
        yata.pointer.scroll(scroll.screen_bounds().center, clicks=20)

        def permission_is_reachable():
            control = executable.screen_bounds()
            viewport = scroll.screen_bounds()
            return viewport.y <= control.y and control.y + control.height <= viewport.y + viewport.height

        yata.wait(permission_is_reachable, "permissions to remain reachable below media details")
        yata.pointer.click(executable)
        yata.wait(
            lambda: fixture_tree.path(name).stat().st_mode & 0o111 == 0o111,
            "the scrolled permission control to remain usable",
        )
    close = dialog.find(role="button", name="Close dialog")
    assert close and close.is_rendered()
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "Properties to close after inspection")
    yata.open_context_menu("readme.md")
    yata.choose_menu_item("Properties")
    dialog = yata.wait_for_dialog()
    yata.wait(lambda: dialog.find(role="label", name="10 B"), "ordinary file properties")
    assert dialog.find(role="label", name="MEDIA") is None


@pytest.mark.preferences(browser_mode="icons", single_click_previews=False)
def test_media_details_are_properties_only(yata):
    yata.select_entry("clip.mp4")
    yata.keyboard.press("space")
    yata.wait(lambda: yata.preview_shows("video/mp4"), "video preview ready")
    yata.open_context_menu("clip.mp4")
    yata.choose_menu_item("Properties")
    dialog = yata.wait_for_dialog()
    yata.wait(
        lambda: dialog.find(role="label", name="320 × 180 pixels", rendered=False),
        "source resolution in Properties",
    )
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "Properties to close")
    preview = yata.preview()
    assert preview is not None
    for name in ["SIZE", "MODIFIED", "TYPE"]:
        assert preview.find(role="label", name=name, rendered=False)
    for name in ["RESOLUTION", "DURATION", "BITRATE", "VIDEO CODEC", "FRAME RATE", "AUDIO CODEC", "SAMPLE RATE", "CHANNELS"]:
        assert preview.find(role="label", name=name, rendered=False) is None
