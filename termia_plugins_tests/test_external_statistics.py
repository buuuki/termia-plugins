# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


def exercise_launch(phase):
    from gi.repository import GLib
    from termia.app import TermiaApp, TermiaWindow
    from termia.constants import STATISTICS_FILE

    def wait_until(predicate):
        deadline = time.monotonic() + 5
        while not predicate():
            if time.monotonic() >= deadline:
                raise AssertionError(f"Timed out in {phase}")
            GLib.MainContext.default().iteration(False)
            time.sleep(0.005)

    app = TermiaApp()
    app.set_application_id(None)
    app.register(None)
    window = TermiaWindow(app)
    window.present()
    check = unittest.TestCase()

    def close_dialog(title):
        wait_until(lambda: any(w.get_title() == title for w in app.get_windows()))
        next(w for w in app.get_windows() if w.get_title() == title).destroy()

    try:
        wait_until(window.get_mapped)
        if phase == "initial":
            check.assertTrue(window.statistics_available())
            menu = window.main_menu_button.get_popover()
            check.assertTrue(menu.activate_action("main-menu.statistics", None))
            close_dialog("Statistics")
            session = window.open_process_terminal_tab("fixture", ["/bin/sh", "-c", "read value"], None)
            wait_until(session.terminal.get_mapped)
            window.on_terminal_right_click(None, 1, 3, 3, session, session.terminal)
            check.assertTrue(window._terminal_context_menus[window].activate_action("terminal-menu.statistics", None))
            close_dialog("Session statistics")
            session.terminal.feed_child(b"finish\n")
            wait_until(lambda: window.store.data.statistics.completed_sessions == 5)
            saved_at_exit = json.loads(STATISTICS_FILE.read_text())
            check.assertEqual(saved_at_exit["completed_sessions"], 5)
            check.assertGreater(saved_at_exit["duration_total"], 9)
            window.session_observer.shutdown(window.session_registry.sessions())
            app.plugins.set_enabled("statistics", False)
        else:
            check.assertFalse(window.statistics_available())
            check.assertIsNone(window.main_menu_actions.statistics)
            check.assertIsNone(window.terminal_menu_actions.session_statistics)
            plugin = app.plugins.plugins["statistics"]
            check.assertFalse(plugin.requested_enabled)
            check.assertEqual(plugin.problem, "addon_missing" if phase == "absent" else "")
            if phase == "reinstalled":
                app.plugins.set_enabled("statistics", True)
                check.assertTrue(window.statistics_available())
        saved = json.loads(STATISTICS_FILE.read_text())
        check.assertEqual((saved["connections"], saved["completed_sessions"]), (7, 5))
        check.assertGreater(saved["duration_total"], 9)
    finally:
        window.destroy()
        app.quit()


class ExternalStatisticsTests(unittest.TestCase):
    def test_profile_survives_removal_and_reinstallation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            state = root / "state"
            plugins = root / "plugins"
            config.mkdir()
            (state / "termia").mkdir(parents=True)
            (config / "settings.json").write_text(json.dumps({"app": {
                "statistics_enabled": True, "language": "en",
                "open_local_terminal_on_startup": False, "restore_sessions_on_startup": False,
            }}))
            history = state / "termia/statistics.json"
            history.write_text(json.dumps({"connections": 7, "completed_sessions": 4, "duration_total": 9}))
            env = dict(os.environ, TERMIA_CONFIG_DIR=str(config), TERMIA_STATE_DIR=str(state),
                       TERMIA_PLUGINS_DIR=str(plugins), TERMIA_DISABLE_PLUGINS="0")
            source = Path(__file__).resolve().parents[1] / "statistics"
            for phase in ("initial", "absent", "reinstalled"):
                with self.subTest(phase=phase):
                    if phase == "absent":
                        shutil.rmtree(plugins / "statistics")
                    else:
                        shutil.copytree(source, plugins / "statistics")
                    subprocess.run([sys.executable, __file__, phase], env=env, check=True, timeout=25)
                    if phase == "initial":
                        expected_history = json.loads(history.read_text())
                    else:
                        self.assertEqual(json.loads(history.read_text()), expected_history)


if __name__ == "__main__":
    exercise_launch(sys.argv[1])
