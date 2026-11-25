"""Exercise the contextual upload UI with an isolated local profile."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def exercise(installed):
    from gi.repository import GLib
    from termia.app import TermiaApp, TermiaWindow
    from termia.constants import SETTINGS_FILE
    from termia.models import Server

    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps({"app": {"open_local_terminal_on_startup": False,
                                               "restore_sessions_on_startup": False}}))
    app = TermiaApp()
    app.set_application_id(None)
    app.register(None)
    window = TermiaWindow(app)
    window.present()
    check = unittest.TestCase()
    try:
        if not installed:
            check.assertIsNone(window.scp_ui())
            check.assertIsNone(window.terminal_menu_actions.send_files)
            return
        server = Server("fixture", "Synthetic", "fixture.invalid", "tester")
        ui = window.scp_ui()
        check.assertIsNotNone(ui)
        # Open the native chooser, then cancel it by disabling the plugin.
        check.assertEqual(ui.show("ca").select_files().get_title(), "Enviar fitxers al servidor")
        window.terminal_menu_actions.send_files(Mock(), None, server)
        pending, = window.file_transfer_controllers
        chooser = pending.file_chooser
        check.assertTrue(chooser.get_visible())
        check.assertTrue(chooser.get_select_multiple())
        app.plugins.set_enabled("scp", False)
        check.assertFalse(chooser.get_visible())
        check.assertNotIn(pending, window.file_transfer_controllers)
        app.plugins.set_enabled("scp", True)
        ui = window.scp_ui()
        # Drive selection without a portal or a network connection.
        selector = Mock()
        views = ui.show("es")
        check.assertEqual(views.select_files().get_title(), "Enviar ficheros al servidor")
        with patch.object(type(views), "select_files", return_value=selector):
            window.terminal_menu_actions.send_files(Mock(), None, server)
        controller, = window.file_transfer_controllers
        selector.show.assert_called_once_with()
        selector.set_transient_for.assert_called_once_with(window)
        controller.show_destination_dialog(server, [Path("fixture.txt")])
        check.assertTrue(controller.pending_destination_dialog.get_visible())
        unrelated = Mock()
        window.register_file_transfer(unrelated)
        app.plugins.set_enabled("scp", False)
        check.assertTrue(controller.cancelled)
        check.assertIsNone(controller.pending_destination_dialog)
        check.assertNotIn(controller, window.file_transfer_controllers)
        unrelated.cancel_active_transfer.assert_not_called()
        check.assertIsNone(window.terminal_menu_actions.send_files)
        app.plugins.set_enabled("scp", True)
        with patch.object(type(views), "select_files", return_value=selector):
            window.terminal_menu_actions.send_files(Mock(), None, server)
        window.unregister_file_transfer(unrelated)
        controller, = window.file_transfer_controllers
        controller.inspect_known_host = lambda host, port, callback: callback(True)
        # Both SSH preparation and SCP copying execute only a local success fixture.
        find = GLib.find_program_in_path
        with patch.object(GLib, "find_program_in_path", side_effect=lambda name:
                          "/bin/true" if name in {"ssh", "scp"} else find(name)):
            controller.start_upload(server, [Path("fixture.txt")], "/synthetic")
            state = controller.active_state
            check.assertTrue(state["dialog"].get_visible())
            deadline = time.monotonic() + 5
            while not state["completed"] and time.monotonic() < deadline:
                GLib.MainContext.default().iteration(False)
                time.sleep(.005)
            check.assertTrue(state["completed"])
            check.assertEqual(state["progress"].get_fraction(), 1.0)
            check.assertNotIn(controller, window.file_transfer_controllers)
            state["dialog"].destroy()
        # Disable with an actual isolated child pending, and leave SFTP alone.
        slow = SETTINGS_FILE.parent / "wait-for-cancel"
        slow.write_text("#!/bin/sh\nexec /bin/sleep 15\n")
        slow.chmod(0o700)
        with patch.object(type(views), "select_files", return_value=selector):
            window.terminal_menu_actions.send_files(Mock(), None, server)
        controller, = window.file_transfer_controllers
        controller.inspect_known_host = lambda host, port, callback: callback(True)
        window.register_file_transfer(unrelated)
        try:
            with patch.object(GLib, "find_program_in_path", side_effect=lambda name:
                              str(slow) if name in {"ssh", "scp"} else find(name)):
                controller.start_upload(server, [Path("fixture.txt")], "/synthetic")
            state = controller.active_state
            check.assertIsNotNone(state["process"])
            app.plugins.set_enabled("scp", False)
            deadline = time.monotonic() + 5
            while controller.shutdown_cleanup_state() == "pending" and time.monotonic() < deadline:
                GLib.MainContext.default().iteration(False)
                time.sleep(.01)
            check.assertEqual(controller.shutdown_cleanup_state(), "stopped")
            check.assertTrue(state["cancelled"])
            unrelated.cancel_active_transfer.assert_not_called()
        finally:
            controller.cancel_active_transfer(close_dialog=True)
            window.unregister_file_transfer(unrelated)

    finally:
        window.destroy()
        app.quit()


class ExternalSCPTests(unittest.TestCase):
    def test_installed_disabled_and_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plugins = root / "plugins"
            env = dict(os.environ, TERMIA_PLUGINS_DIR=str(plugins),
                       TERMIA_CONFIG_DIR=str(root / "config"), TERMIA_STATE_DIR=str(root / "state"),
                       TERMIA_DISABLE_PLUGINS="0")
            shutil.copytree(Path(__file__).resolve().parents[1] / "scp", plugins / "scp")
            subprocess.run([sys.executable, __file__, "installed"], check=True, env=env, timeout=25)
            shutil.rmtree(plugins / "scp")
            subprocess.run([sys.executable, __file__, "absent"], check=True, env=env, timeout=25)


if __name__ == "__main__":
    exercise(sys.argv[1] == "installed")
