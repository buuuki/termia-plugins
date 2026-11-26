"""Exercise the packaged explorer through a real Termia window."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch


def exercise(mode):
    from gi.repository import GLib
    from termia.app import TermiaApp, TermiaWindow
    from termia.models import Server
    from termia.sftp_connection import SFTPConnection

    app = TermiaApp()
    app.set_application_id(None)
    app.register(None)
    window = TermiaWindow(app)
    window.present()
    check = unittest.TestCase()
    backend = Mock()
    backend.connect.return_value = "/fixture"
    backend.list_directory.return_value = []
    original_create = SFTPConnection.create_service

    def create_service(connection, dispatch):
        connection.backend_factory = lambda endpoint: backend
        return original_create(connection, dispatch)

    def wait_for(predicate):
        deadline = time.monotonic() + 5
        while not predicate():
            if time.monotonic() > deadline:
                raise AssertionError("Timed out waiting for SFTP")
            GLib.MainContext.default().iteration(False)
            time.sleep(.005)

    try:
        if mode == "absent":
            check.assertIsNone(window.terminal_menu_actions.browse_files)
            return
        check.assertIsNone(window.terminal_menu_actions.browse_files)
        check.assertFalse(app.plugins.plugins["sftp"].requested_enabled)
        app.plugins.set_enabled("sftp", True)
        server = Server("fixture", "Synthetic", "fixture.invalid", "tester")
        callback = window.terminal_menu_actions.browse_files
        check.assertIsNotNone(callback)
        with patch.object(SFTPConnection, "create_service", create_service):
            callback(Mock(), None, server)
            wait_for(lambda: any(view.connection_ready and not view.service.busy
                                 for view in window.sftp_tool.transfers))
            view, = window.sftp_tool.transfers
            started, release = Event(), Event()

            def upload(*_args):
                started.set()
                release.wait(3)

            backend.upload.side_effect = upload
            backend.close.side_effect = release.set
            view.upload_paths([Path("fixture.txt")])
            check.assertTrue(started.wait(2))
            other = Mock()
            window.register_file_transfer(other)
            app.plugins.set_enabled("sftp", False)
            check.assertIsNone(window.terminal_menu_actions.browse_files)
            wait_for(lambda: not window.sftp_tool.transfers)
            backend.close.assert_called()
            other.cancel_active_transfer.assert_not_called()
            window.unregister_file_transfer(other)
        # A deferred launch requested before disable must not reopen the explorer.
        app.plugins.set_enabled("sftp", True)
        window.browse_sftp(Mock(), None, server)
        app.plugins.set_enabled("sftp", False)
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        check.assertFalse(window.sftp_tool.transfers)
    finally:
        window.sftp_tool.cancel_all()
        window.destroy()
        app.quit()


class ExternalSFTPTests(unittest.TestCase):
    def test_preference_and_cleanup_survive_external_distribution(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config"
            config.mkdir()
            settings = config / "settings.json"
            settings.write_text(json.dumps({"app": {
                "sftp_enabled": False, "open_local_terminal_on_startup": False,
                "restore_sessions_on_startup": False,
            }}))
            plugins = root / "plugins"
            source = Path(__file__).resolve().parents[1] / "sftp"
            env = dict(os.environ, TERMIA_CONFIG_DIR=str(config),
                       TERMIA_PLUGINS_DIR=str(plugins), TERMIA_STATE_DIR=str(root / "state"),
                       TERMIA_DISABLE_PLUGINS="0")
            shutil.copytree(source, plugins / "sftp")
            subprocess.run([sys.executable, __file__, "installed"], env=env, check=True, timeout=30)
            self.assertEqual((config / "plugins/sftp-addon.disabled").read_text().strip(), "disabled")
            self.assertFalse(json.loads(settings.read_text())["app"]["sftp_enabled"])
            shutil.rmtree(plugins / "sftp")
            subprocess.run([sys.executable, __file__, "absent"], env=env, check=True, timeout=30)
            self.assertEqual((config / "plugins/sftp-addon.disabled").read_text().strip(), "disabled")
            settings.write_text(json.dumps({"app": {"sftp_enabled": True,
                                                       "open_local_terminal_on_startup": False,
                                                       "restore_sessions_on_startup": False}}))
            shutil.copytree(source, plugins / "sftp")
            subprocess.run([sys.executable, __file__, "installed"], env=env, check=True, timeout=30)


if __name__ == "__main__":
    exercise(sys.argv[1])
