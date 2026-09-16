# SPDX-License-Identifier: MIT
import os
import shutil
import struct
import zipfile
import zlib
from pathlib import Path

import pytest

from harness.artifacts import ArtifactCollector


ARCHIVE_FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.mark.parametrize("format", ["7Z", "TAR.GZ"])
def test_cancel_compression_stops_before_publishing_and_allows_another_operation(yata, format):
    fixture = yata.fixture
    fixture.path("payload.bin").write_bytes(os.urandom(16 * 1024 * 1024))
    yata.entry("payload.bin")
    yata.open_context_menu("payload.bin")
    yata.choose_menu_item("Compress…")
    dialog = yata.wait_for_dialog()
    yata.pointer.click(dialog.find(role="toggle button", name=format))
    yata.pointer.click(yata.dialog_button("Compress"))
    yata.wait(
        lambda: (dialog := yata.dialog()) is not None
        and dialog.name == "Processing archive…"
        and dialog.find(role="label", name="Preparing…") is not None,
        "immediate preparation feedback",
    )
    yata.pointer.click(yata.dialog_button("Cancel"))
    yata.wait(
        lambda: (dialog := yata.dialog()) is not None and dialog.name == "Operation cancelled",
        "compression worker to stop and report cancellation",
    )
    assert not yata.window.find(role="progress bar")
    assert not list(fixture.root.glob(".strata-compression-*"))
    assert not list(fixture.root.glob("*.7z"))
    assert not list(fixture.root.glob("*.tar.gz"))
    assert fixture.path("payload.bin").stat().st_size == 16 * 1024 * 1024
    yata.pointer.click(yata.dialog_button("Close"))
    yata.wait(lambda: yata.dialog() is None, "cancellation summary dismissal")

    yata.open_context_menu("todo.txt")
    yata.choose_menu_item("Compress…")
    yata.wait_for_dialog()
    yata.pointer.click(yata.dialog_button("Compress"))
    yata.wait(lambda: fixture.path("todo.txt.zip").exists(), "subsequent compression")
    yata.wait(lambda: yata.dialog() is None, "subsequent progress dismissal")
    with zipfile.ZipFile(fixture.path("todo.txt.zip")) as archive:
        assert archive.read("todo.txt") == fixture.path("todo.txt").read_bytes()


@pytest.mark.parametrize("name", ["fake.zip", "fake.7z", "fake.tar", "fake.tar.gz", "fake.rar"])
def test_invalid_archive_reports_damage_and_allows_another_extraction(yata, name):
    fixture = yata.fixture
    fixture.path(name).write_bytes(b"This is harmless text, not an archive.\n")
    with zipfile.ZipFile(fixture.path("valid.zip"), "w") as archive:
        archive.writestr("extracted.txt", "harmless contents")
    yata.keyboard.press("ctrl+r")
    yata.pointer.right_click(yata.entry(name))
    yata.choose_menu_item("Extract here")
    dialog = yata.wait(
        lambda: (
            dialog
            if (dialog := yata.dialog()) is not None
            and dialog.name == "Unable to complete operation"
            else None
        ),
        "the archive error dialog to replace the progress dialog",
    )
    assert dialog.find(role="label", name="This file is not a valid archive or is damaged.")
    assert not yata.window.find(role="progress bar")
    assert fixture.path(name).read_bytes() == b"This is harmless text, not an archive.\n"
    yata.pointer.click(yata.dialog_button("Close"))
    yata.wait(lambda: yata.dialog() is None, "error dismissal")
    yata.pointer.right_click(yata.entry("valid.zip"))
    yata.choose_menu_item("Extract here")
    yata.wait(lambda: fixture.path("extracted.txt").exists(), "valid archive extraction")
    assert fixture.path("extracted.txt").read_text() == "harmless contents"
    yata.wait(lambda: yata.dialog() is None, "extraction progress dismissal")


@pytest.mark.parametrize("source,password,member,contents", [
    (ARCHIVE_FIXTURES / "content-encrypted.7z", "secret", "protected.txt", "password retry works\n"),
    (Path(__file__).parents[2] / "fixtures/rar/encrypted.rar", "unrar", ".gitignore", "target\nCargo.lock\n"),
    (Path(__file__).parents[2] / "fixtures/rar/comment-hpw-password.rar", "password", ".gitignore", "target\nCargo.lock\n"),
])
def test_wrong_extract_password_reopens_dialog_until_password_is_correct(yata, source, password, member, contents):
    fixture = yata.fixture
    archive_name = source.name
    shutil.copyfile(source, fixture.path(archive_name))
    yata.keyboard.press("ctrl+r")
    yata.pointer.right_click(yata.entry(archive_name))
    yata.choose_menu_item("Extract here")

    dialog = yata.wait(
        lambda: (
            dialog
            if (dialog := yata.dialog()) is not None and dialog.name == "Extract"
            else None
        ),
        "the password dialog to replace the progress dialog",
    )
    yata.pointer.click(yata.dialog_button("Extract"))
    dialog = yata.wait_for_dialog()
    assert dialog.find(role="label", name="Enter a password") is not None

    yata.keyboard.type_text("wrong")
    yata.pointer.click(yata.dialog_button("Extract"))

    dialog = yata.wait(
        lambda: (
            dialog
            if (dialog := yata.dialog()) is not None
            and dialog.name == "Extract"
            and dialog.find(role="password text", states={"focused"}) is not None
            else None
        ),
        "the password dialog to reopen after the wrong password",
    )
    assert dialog.find(role="label", name="Invalid password") is not None
    assert dialog.find(role="label", name="Unable to complete operation") is None

    if source.suffix == ".rar":
        collector = ArtifactCollector(test_name=f"rar-password-{source.stem}")
        yata.screenshot(collector.directory / "password-retry.png")
    yata.keyboard.type_text(password)
    yata.pointer.click(yata.dialog_button("Extract"))
    extracted = fixture.path(member)
    yata.wait(lambda: extracted.exists(), "the archive to extract with the correct password")
    yata.wait(lambda: yata.dialog() is None, "extraction progress dismissal")
    assert extracted.read_text() == contents


def test_cancelled_extract_to_does_not_hijack_later_extract_here(yata):
    fixture = yata.fixture
    archive_name = "content-encrypted.7z"
    shutil.copyfile(ARCHIVE_FIXTURES / archive_name, fixture.path(archive_name))
    with zipfile.ZipFile(fixture.path("later.zip"), "w") as archive:
        archive.writestr("later.txt", "later extraction\n")
    yata.keyboard.press("ctrl+r")
    yata.open_context_menu(archive_name)
    yata.choose_menu_item("Extract to…")
    destination = fixture.path("leftover")
    field = yata.editable_field()
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text(str(destination))
    yata.wait(lambda: field.text == str(destination), "the destination field")
    yata.keyboard.press("Return")
    yata.wait(
        lambda: (dialog := yata.dialog()) is not None and dialog.name == "Extract",
        "the password prompt",
    )
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "password prompt cancellation")
    assert not destination.exists()
    yata.open_context_menu("later.zip")
    yata.choose_menu_item("Extract here")
    yata.wait(lambda: fixture.path("later.txt").exists(), "later extraction")
    yata.wait(lambda: yata.dialog() is None, "extraction progress dismissal")
    assert yata.current_directory() == fixture.root.name
    assert fixture.path("later.txt").read_text() == "later extraction\n"
    assert not destination.exists()
    yata.entry("later.txt")
    collector = ArtifactCollector(test_name="cancelled-extract-to")
    yata.screenshot(collector.directory / "after.png")


_CRCTABLE = None


def _zipcrypto_crc32(ch, crc):
    global _CRCTABLE
    if _CRCTABLE is None:
        table = []
        for value in range(256):
            for _ in range(8):
                value = (value >> 1) ^ 0xEDB88320 if value & 1 else value >> 1
            table.append(value)
        _CRCTABLE = table
    return (crc >> 8) ^ _CRCTABLE[(crc ^ ch) & 0xFF]


def _zipcrypto_encrypt(password, data):
    key0, key1, key2 = 305419896, 591751049, 878082192

    def update(byte):
        nonlocal key0, key1, key2
        key0 = _zipcrypto_crc32(byte, key0)
        key1 = (key1 + (key0 & 0xFF)) & 0xFFFFFFFF
        key1 = (key1 * 134775813 + 1) & 0xFFFFFFFF
        key2 = _zipcrypto_crc32(key1 >> 24, key2)

    for byte in password:
        update(byte)
    out = bytearray()
    for byte in data:
        key = key2 | 2
        out.append(byte ^ (((key * (key ^ 1)) >> 8) & 0xFF))
        update(byte)
    return bytes(out)


def _raw_deflate(data):
    compressor = zlib.compressobj(level=9, wbits=-15)
    return compressor.compress(data) + compressor.flush()


def _write_zipcrypto(path, password, name, contents, *, deflated=False):
    crc = zlib.crc32(contents) & 0xFFFFFFFF
    payload = _raw_deflate(contents) if deflated else contents
    header = os.urandom(11) + bytes([(crc >> 24) & 0xFF])
    encrypted = _zipcrypto_encrypt(password, header + payload)
    name_b = name.encode("utf-8")
    flags = 0x0001
    method = 8 if deflated else 0
    local = struct.pack(
        "<IHHHHHIIIHH",
        0x04034B50,
        20,
        flags,
        method,
        0,
        0,
        crc,
        len(encrypted),
        len(contents),
        len(name_b),
        0,
    )
    local_data = local + name_b + encrypted
    central = struct.pack(
        "<IHHHHHHIIIHHHHHII",
        0x02014B50,
        20,
        20,
        flags,
        method,
        0,
        0,
        crc,
        len(encrypted),
        len(contents),
        len(name_b),
        0,
        0,
        0,
        0,
        0,
        0,
    )
    cd = central + name_b
    eocd = struct.pack(
        "<IHHHHIIH",
        0x06054B50,
        0,
        0,
        1,
        1,
        len(cd),
        len(local_data),
        0,
    )
    path.write_bytes(local_data + cd + eocd)


def _zipcrypto_crc_collision(path, member="some.txt"):
    for candidate in range(4096):
        password = str(candidate).encode()
        try:
            with zipfile.ZipFile(path) as archive:
                archive.read(member, pwd=password)
        except RuntimeError as error:
            if "Bad password" in str(error):
                continue
            return str(candidate)
        except (zipfile.BadZipFile, OSError, zlib.error):
            return str(candidate)
    raise AssertionError("no ZipCrypto CRC collision in 0..4096")


@pytest.mark.parametrize(
    "deflated,contents",
    [
        pytest.param(False, b"hello from zipcrypto", id="stored"),
        pytest.param(True, b"hello from zipcrypto\n" * 64, id="deflated"),
    ],
)
def test_zipcrypto_collision_reopens_extract_dialog(yata, deflated, contents):
    fixture = yata.fixture
    archive_name = "password.zip"
    archive_path = fixture.path(archive_name)
    _write_zipcrypto(
        archive_path, b"zipsecret", "some.txt", contents, deflated=deflated
    )
    collision = _zipcrypto_crc_collision(archive_path)
    yata.keyboard.press("ctrl+r")
    yata.pointer.right_click(yata.entry(archive_name))
    yata.choose_menu_item("Extract here")

    dialog = yata.wait(
        lambda: (
            dialog
            if (dialog := yata.dialog()) is not None and dialog.name == "Extract"
            else None
        ),
        "the password dialog to replace the progress dialog",
    )
    yata.pointer.click(yata.dialog_button("Extract"))
    dialog = yata.wait_for_dialog()
    assert dialog.find(role="label", name="Enter a password") is not None

    yata.keyboard.type_text(collision)
    yata.pointer.click(yata.dialog_button("Extract"))

    dialog = yata.wait(
        lambda: (
            dialog
            if (dialog := yata.dialog()) is not None
            and dialog.name == "Extract"
            and dialog.find(role="password text", states={"focused"}) is not None
            else None
        ),
        "the password dialog to reopen after a ZipCrypto CRC collision",
    )
    assert dialog.find(role="label", name="Invalid password") is not None
    assert dialog.find(role="label", name="Unable to complete operation") is None
    assert dialog.find(role="label", name="This file is not a valid archive or is damaged.") is None

    yata.keyboard.type_text("zipsecret")
    yata.pointer.click(yata.dialog_button("Extract"))
    extracted = fixture.path("some.txt")
    yata.wait(lambda: extracted.exists(), "the archive to extract with the correct password")
    assert extracted.read_text() == contents.decode()
    yata.wait(lambda: yata.dialog() is None, "extraction progress dismissal")
