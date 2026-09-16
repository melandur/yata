# SPDX-License-Identifier: MIT

import pytest
from gi.repository import Gio


@pytest.fixture
def open_with_app(test_environment):
    applications = test_environment.data_home / "applications"
    applications.mkdir()
    output = test_environment.root / "opened-files"
    launcher = test_environment.root / "record-files"
    launcher.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{output}"\n')
    launcher.chmod(0o755)
    (applications / "strata-review.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Review Text Viewer\n"
        f"Exec={launcher} %U\nMimeType=text/plain;inode/directory;\nNoDisplay=false\n"
    )
    associations = test_environment.config_home / "mimeapps.list"
    contents = (
        "[Default Applications]\ntext/plain=strata-review.desktop;\n"
        "inode/directory=strata-review.desktop;\n"
        "[Added Associations]\ntext/plain=strata-review.desktop;\n"
        "inode/directory=strata-review.desktop;\n"
    )
    associations.write_text(contents)
    return output, associations, contents

@pytest.fixture
def activation_fallback_app(open_with_app):
    output, associations, _ = open_with_app
    contents = associations.read_text().replace(
        "text/plain=strata-review.desktop;\n",
        "",
    )
    associations.write_text(contents)
    return output, associations, contents


@pytest.fixture
def empty_application_data(test_environment, monkeypatch):
    data_dirs = test_environment.root / "empty-data-dirs"
    data_dirs.mkdir()
    variables = test_environment.variables
    monkeypatch.setattr(
        test_environment,
        "variables",
        lambda: {**variables(), "XDG_DATA_DIRS": str(data_dirs)},
    )


def test_activation_without_default_opens_with_visible_application(
    activation_fallback_app, yata
):
    output, associations, contents = activation_fallback_app
    expected = yata.fixture.path("todo.txt")
    yata.select_entry_with_keyboard("todo.txt")
    yata.keyboard.press("Return")

    dialog = yata.wait_for_dialog()
    assert "Review Text Viewer" in dialog.dump()
    yata.keyboard.type_text("Review Text Viewer")
    yata.keyboard.press("Return")
    yata.wait(
        lambda: output.exists() and output.read_text(),
        "the selected application to receive the activated file",
    )

    received = output.read_text().splitlines()
    assert len(received) == 1
    assert Gio.File.new_for_commandline_arg(received[0]).equal(
        Gio.File.new_for_path(str(expected))
    )
    assert associations.read_text() == contents
    yata.wait(lambda: yata.dialog() is None, "the chooser to close")
    yata.wait_for_focused_entry("todo.txt")


def test_activation_without_selectable_application_shows_specific_empty_state(
    empty_application_data, yata
):
    yata.select_entry_with_keyboard("todo.txt")
    yata.keyboard.press("Return")

    dialog = yata.wait_for_dialog()
    yata.wait(
        lambda: dialog.find(
            role="label", name="No application is registered for this file"
        )
        is not None,
        "the activation-specific empty feedback",
        timeout=3.0,
    )
    assert "sensitive" not in yata.dialog_button("Open").states

    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "the empty chooser to close")
    yata.wait_for_focused_entry("todo.txt")


@pytest.mark.parametrize("target", ["todo.txt", "documents", "background"])
def test_open_with_launches_without_changing_default(open_with_app, yata, target):
    output, associations, contents = open_with_app
    if target == "background":
        expected = yata.fixture.root
        yata.pointer.right_click(yata.pane(), at=yata.background_point())
        yata.wait(lambda: "Open With…" in yata.menu_items(), "folder menu")
    else:
        expected = yata.fixture.path(target)
        yata.open_context_menu(target)
        yata.wait(lambda: "sensitive" in yata.menu_item("Open With…").states, "MIME lookup")
    yata.choose_menu_item("Open With…")
    dialog = yata.wait_for_dialog()
    assert "Review Text Viewer" in dialog.dump()
    yata.keyboard.press("Return")
    yata.wait(
        lambda: output.exists() and output.read_text(),
        "the selected application to receive the target",
    )
    received = output.read_text().splitlines()
    assert len(received) == 1
    assert Gio.File.new_for_commandline_arg(received[0]).equal(
        Gio.File.new_for_path(str(expected))
    )
    assert associations.read_text() == contents
    yata.wait(lambda: yata.dialog() is None, "the chooser to close")


def test_open_with_launch_failure_shows_an_error(open_with_app, yata):
    output, associations, contents = open_with_app
    yata.open_context_menu("todo.txt")
    yata.wait(lambda: "sensitive" in yata.menu_item("Open With…").states, "MIME lookup")
    yata.choose_menu_item("Open With…")
    yata.wait_for_dialog()
    (output.parent / "record-files").unlink()
    yata.keyboard.press("Return")
    yata.wait(
        lambda: yata.dialog() is not None
        and yata.dialog().name == "Unable to open file",
        "the launch error dialog",
    )
    assert not output.exists()
    assert associations.read_text() == contents
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "the error dialog to close")


@pytest.fixture
def chooser_apps(open_with_app, test_environment):
    output, associations, _ = open_with_app
    applications = test_environment.data_home / "applications"
    launcher = test_environment.root / "record-files"
    for filename, name, extra in [
        ("strata-review", "Review Text Viewer", "NoDisplay=true\n"),
        ("strata-alternative", "Alternative Viewer", "Icon=strata-nonexistent-icon-569\n"),
        ("strata-missing", "Missing Icon Viewer", ""),
        ("strata-other-desktop", "Other Desktop Viewer", "OnlyShowIn=StrataTestDesktop;\n"),
    ]:
        (applications / f"{filename}.desktop").write_text(
            f"[Desktop Entry]\nType=Application\nName={name}\n"
            f"Exec={launcher} %U\nMimeType=text/plain;text/markdown;\n{extra}"
        )
    ids = "strata-review.desktop;strata-alternative.desktop;strata-missing.desktop;strata-other-desktop.desktop;"
    contents = (
        "[Default Applications]\n"
        "text/plain=strata-review.desktop;\ntext/markdown=strata-review.desktop;\n"
        f"[Added Associations]\ntext/plain={ids}\ntext/markdown={ids}\n"
    )
    associations.write_text(contents)
    return output, associations, contents


def test_open_with_names_rows_and_tabs_out_of_the_list(chooser_apps, yata):
    yata.open_context_menu("todo.txt")
    yata.wait(lambda: "sensitive" in yata.menu_item("Open With…").states, "MIME lookup")
    yata.choose_menu_item("Open With…")
    dialog = yata.wait_for_dialog()
    # Section headers are not selectable and carry their text in a child label.
    all_rows = dialog.find_all(role="list item")
    sections: dict[str, list[str]] = {}
    current_section = None
    for row in all_rows:
        if "selectable" not in row.states:
            current_section = next((c.name for c in row.children if c.name), "")
            sections.setdefault(current_section, [])
        elif current_section is not None:
            sections[current_section].append(row.name)
    recommended = sections.get("Recommended Applications", [])
    assert recommended[0] == "Review Text Viewer"
    assert {"Alternative Viewer", "Missing Icon Viewer"} <= set(recommended)
    assert recommended[1:] == sorted(recommended[1:], key=str.lower)
    assert all(recommended)
    assert "Other Desktop Viewer" not in [row.name for row in all_rows]
    yata.wait(
        lambda: yata.focused_node() is not None and "editable" in yata.focused_node().states,
        "search entry focused on open",
    )
    yata.keyboard.press("Down")
    yata.wait(lambda: "editable" in yata.focused_node().states, "search retains focus")
    yata.wait(
        lambda: any(row.name == "Alternative Viewer" and "selected" in row.states
                    for row in yata.dialog().find_all(role="list item")),
        "arrow selection",
    )
    assert "editable" in yata.focused_node().states
    yata.keyboard.press("Tab")
    yata.wait(lambda: yata.focused_node().name == "Alternative Viewer", "Tab into list")
    yata.keyboard.press("Tab")
    yata.wait(lambda: yata.focused_node().name == "Cancel", "Tab to leave the list")
    yata.keyboard.press("shift+Tab")
    yata.wait(lambda: yata.focused_node().name == "Alternative Viewer", "selected row focus")
    yata.keyboard.press("Tab")
    yata.keyboard.press("Tab")
    yata.wait(lambda: yata.focused_node().name == "Open", "Tab to reach Open")


def test_open_with_search_filters_and_escape_clears(chooser_apps, yata, request):
    from harness.artifacts import ArtifactCollector

    yata.open_context_menu("todo.txt")
    yata.wait(lambda: "sensitive" in yata.menu_item("Open With…").states, "MIME lookup")
    yata.choose_menu_item("Open With…")
    yata.wait_for_dialog()
    yata.keyboard.type_text("ALTERNATIVE")
    yata.keyboard.press("Down")
    yata.wait(lambda: "editable" in yata.focused_node().states, "search retains focus after Down")
    yata.keyboard.press("Up")
    assert "editable" in yata.focused_node().states
    yata.keyboard.type_text("x")
    yata.wait(
        lambda: "No matching applications were found." in yata.dialog().dump(),
        "typing after arrow navigation appends at the caret",
    )
    yata.keyboard.press("BackSpace")
    yata.wait(lambda: "Alternative Viewer" in yata.dialog().dump(), "Backspace restores match")
    collector = ArtifactCollector(test_name=request.node.name)
    yata.screenshot(collector.directory / "filtered-chooser.png")
    yata.keyboard.press("ctrl+a")
    yata.keyboard.type_text("no-such-application-821")
    yata.wait(
        lambda: "No matching applications were found." in yata.dialog().dump(),
        "empty search feedback",
    )
    yata.keyboard.press("Return")
    assert yata.dialog() is not None
    yata.keyboard.press("Escape")
    yata.wait(lambda: "No matching applications were found." not in yata.dialog().dump(), "cleared search")
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "dismissed chooser")


@pytest.mark.parametrize("action", ["Open", "Open With…"])
def test_open_with_mixed_types_share_a_hidden_default(chooser_apps, yata, action):
    output, associations, contents = chooser_apps
    yata.select_entry("todo.txt")
    yata.pointer.click(yata.entry("readme.md"), modifiers=["ctrl"])
    yata.wait_for_selection(["readme.md", "todo.txt"])
    yata.open_context_menu("todo.txt")
    yata.wait(lambda: "Open" in yata.menu_items(), "shared default lookup")
    yata.choose_menu_item(action)
    if action == "Open With…":
        yata.wait_for_dialog()
        yata.keyboard.press("Return")
    yata.wait(lambda: output.exists() and len(output.read_text().splitlines()) == 2, "both files to open")
    received = [Gio.File.new_for_commandline_arg(value) for value in output.read_text().splitlines()]
    for name in ["todo.txt", "readme.md"]:
        assert any(file.equal(Gio.File.new_for_path(str(yata.fixture.path(name)))) for file in received)
    assert associations.read_text() == contents


@pytest.fixture
def different_defaults(chooser_apps):
    _, associations, contents = chooser_apps
    associations.write_text(contents.replace(
        "text/markdown=strata-review.desktop;\n",
        "text/markdown=strata-alternative.desktop;\n",
        1,
    ))


def test_open_with_common_handlers_do_not_imply_a_shared_default(different_defaults, yata):
    yata.select_entry("todo.txt")
    yata.pointer.click(yata.entry("readme.md"), modifiers=["ctrl"])
    yata.wait_for_selection(["readme.md", "todo.txt"])
    yata.open_context_menu("todo.txt")
    yata.wait(lambda: "sensitive" in yata.menu_item("Open With…").states, "common handlers")
    assert "Open" not in yata.menu_items()
    yata.choose_menu_item("Open With…")
    assert "Alternative Viewer" in yata.wait_for_dialog().dump()


@pytest.fixture
def incompatible_files(fixture_tree, open_with_app, test_environment):
    fixture_tree.path("unknown.bin").write_bytes(bytes(range(256)))
    fixture_tree.path("broken-link").symlink_to("missing-target")
    fixture_tree.path("image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    associations = test_environment.config_home / "mimeapps.list"
    with associations.open("a") as stream:
        stream.write("image/png=strata-image.desktop;\n")
    applications = test_environment.data_home / "applications"
    (applications / "strata-image.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Image Viewer\nExec=/bin/true %U\nMimeType=image/png;\n"
    )


def test_open_with_broken_link_is_disabled(incompatible_files, yata):
    yata.open_context_menu("broken-link")
    yata.wait(
        lambda: "Broken symbolic links cannot be opened with an application"
        in yata.menu_item("Open With…").description,
        "MIME lookup result",
    )
    option = yata.menu_item("Open With…")
    assert "sensitive" not in option.states
    yata.keyboard.press("Escape")
    assert yata.dialog() is None


def test_open_with_unknown_type_offers_other_apps(incompatible_files, yata):
    yata.open_context_menu("unknown.bin")
    yata.wait(lambda: "sensitive" in yata.menu_item("Open With…").states, "other apps available")
    yata.choose_menu_item("Open With…")
    dialog = yata.wait_for_dialog()
    dump = dialog.dump()
    assert "Other Applications" in dump
    assert "Recommended Applications" not in dump
    assert "Image Viewer" in dump
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "the chooser to close")


def test_open_with_incompatible_types_offers_other_apps(incompatible_files, yata):
    yata.select_entry("todo.txt")
    yata.pointer.click(yata.entry("image.png"), modifiers=["ctrl"])
    yata.wait_for_selection(["image.png", "todo.txt"])
    yata.open_context_menu("todo.txt")
    yata.wait(lambda: "sensitive" in yata.menu_item("Open With…").states, "other apps available")
    assert "Open" not in yata.menu_items()
    yata.choose_menu_item("Open With…")
    dialog = yata.wait_for_dialog()
    dump = dialog.dump()
    assert "Other Applications" in dump
    assert "Recommended Applications" not in dump
    assert "Image Viewer" in dump
    assert "Review Text Viewer" in dump
    yata.keyboard.press("Escape")
    yata.wait(lambda: yata.dialog() is None, "the chooser to close")
