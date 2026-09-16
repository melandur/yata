# SPDX-License-Identifier: MIT
import io
import shutil
import tarfile
import zipfile
from pathlib import Path

import pytest

from harness.artifacts import ArtifactCollector



@pytest.mark.preferences(
    list_file_clicks=2, grid_file_clicks=2, explorer_file_clicks=2,
)
@pytest.mark.parametrize("activation", ["keyboard", "double-click"])
@pytest.mark.parametrize("format", ["zip", "rar", "tar.gz"])
def test_archive_activation_extracts_to_subfolder(yata, activation, format):
    yata.wait_for_focused_entry("archive")
    fixture = yata.fixture
    archive_name = f"activation.{format}"
    if format == "zip":
        with zipfile.ZipFile(fixture.path(archive_name), "w") as archive:
            archive.writestr("activated.txt", "extracted by activation\n")
        member, contents = "activated.txt", "extracted by activation\n"
    elif format == "tar.gz":
        member, contents = "activated.txt", "extracted by activation\n"
        with tarfile.open(fixture.path(archive_name), "w:gz") as archive:
            info = tarfile.TarInfo(member)
            info.size = len(contents.encode())
            archive.addfile(info, io.BytesIO(contents.encode()))
    else:
        shutil.copyfile(Path(__file__).parents[2] / "fixtures/rar/version.rar", fixture.path(archive_name))
        member, contents = "VERSION", "unrar-0.4.0"
    yata.entry(archive_name)

    if activation == "keyboard":
        yata.select_entry("todo.txt")
        yata.select_entry_with_keyboard(archive_name)
        yata.keyboard.press("Return")
    else:
        yata.double_click_entry(archive_name)

    subfolder = fixture.path("activation")
    extracted = subfolder / member
    yata.wait(lambda: extracted.exists(), "archive activation to extract into a subfolder")
    yata.wait(lambda: yata.dialog() is None, "extraction progress dismissal")
    assert extracted.read_text() == contents
    assert not fixture.path(member).exists()
    assert fixture.path(archive_name).exists()
    assert yata.pane().name == fixture.root.name
    yata.entry("activation")
    extracted.write_text("keep existing edits\n")
    for suffix in [1, 2]:
        if activation == "keyboard":
            yata.select_entry("todo.txt")
            yata.select_entry_with_keyboard(archive_name)
            yata.keyboard.press("Return")
        else:
            yata.double_click_entry(archive_name)
        fresh = fixture.path(f"activation ({suffix})") / member
        yata.wait(lambda: fresh.exists(), "repeated activation to use a fresh folder")
        yata.wait(lambda: yata.dialog() is None, "extraction progress dismissal")
        assert fresh.read_text() == contents
        assert extracted.read_text() == "keep existing edits\n"
        yata.entry(f"activation ({suffix})")
    if format == "rar":
        collector = ArtifactCollector(test_name=f"rar-activation-{activation}")
        yata.screenshot(collector.directory / "after.png")
