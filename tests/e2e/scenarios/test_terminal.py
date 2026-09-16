# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from harness import environment as harness_environment


@pytest.fixture
def test_environment():
    """Empty PATH so launcher availability does not depend on the host."""

    environment = harness_environment.TestEnvironment()
    inherited = environment.variables
    empty_path = environment.root / "empty-path"
    empty_path.mkdir()

    def variables():
        return {**inherited(), "PATH": str(empty_path)}

    environment.variables = variables
    try:
        yield environment
    finally:
        environment.cleanup()


def test_opening_a_terminal_without_an_emulator_reports_no_terminal_found(yata):
    yata.keyboard.press("ctrl+t")

    dialog = yata.wait_for_dialog()
    assert dialog.name == "Unable to open terminal", (
        f"unexpected dialog {dialog.name!r}"
    )
    assert any(
        "No terminal emulator" in node.name for node in dialog.find_all(role="label")
    ), f"the error should explain that no terminal was found\n{dialog.dump()}"

    yata.pointer.click(yata.dialog_button("Close"))
    yata.wait(lambda: yata.dialog() is None, "the dialog to close")
