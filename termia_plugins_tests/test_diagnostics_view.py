# SPDX-License-Identifier: GPL-3.0-or-later
import time
import unittest
from threading import Event
from unittest.mock import Mock

from termia_plugins_tests.diagnostics_plugin_support import plugin_module

code = plugin_module("diagnostics")
view = plugin_module("diagnostics_view")
translator = plugin_module("i18n").translator
DiagnosticContext = code.DiagnosticContext
ProcessReading = code.ProcessReading
ProcessSample = code.ProcessSample
ResourceSnapshot = code.ResourceSnapshot
DiagnosticsTool = view.DiagnosticsTool
DiagnosticsWindow = view.DiagnosticsWindow
GLib, Gtk = view.GLib, view.Gtk


def settle(predicate=lambda: False, seconds=0.5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not predicate():
        GLib.MainContext.default().iteration(False)
        time.sleep(0.002)


class DiagnosticsViewTests(unittest.TestCase):
    def test_metrics_history_and_monitor_stop(self):
        main = ProcessSample(ProcessReading(10, 1, "1", "python3", 10, 1048576, 2, "S"), 25, 8, "child", False)
        child = ProcessSample(ProcessReading(11, 10, "2", "bash", 5, 2097152, 1, "S"), 5, 4, "shell", True)
        snapshot = ResourceSnapshot(1, main, (child,), DiagnosticContext(1, 2, 1, 1), False)
        sampler = Mock()
        sampler.sample.return_value = snapshot
        window = DiagnosticsWindow(None, DiagnosticContext, translator("en"), Mock(), sampler=sampler)
        self.addCleanup(window.destroy)
        window.present()
        settle(lambda: window.values["main", "memory"].get_text() != "—")
        self.assertEqual(window.values["main", "memory"].get_text(), "1.0 MiB")
        self.assertEqual(window.values["children", "memory"].get_text(), "2.0 MiB")
        self.assertEqual(window.values["main", "cpu"].get_text(), "25.0%")
        self.assertTrue(window.orphans.get_visible())
        self.assertFalse(window.history_expander.get_expanded())
        buffer = window.history_view.get_buffer()
        changed = Mock()
        buffer.connect("changed", changed)
        for _ in range(3):
            window.render(snapshot)
        self.assertEqual(len(window.history), 0)
        changed.assert_not_called()
        window.history_expander.set_expanded(True)
        for _ in range(70):
            window.render(snapshot)
        self.assertEqual(len(window.history), 60)
        self.assertEqual(buffer.get_line_count(), 62)  # Heading, samples, trailing newline.
        retained = tuple(window.history)
        window.history_expander.set_expanded(False)
        changed.reset_mock()
        for _ in range(3):
            window.render(snapshot)
        self.assertEqual(tuple(window.history), retained)
        changed.assert_not_called()
        window.history_expander.set_expanded(True)
        self.assertEqual(len(window.history), 0)
        window.render(snapshot)
        self.assertEqual(len(window.history), 1)
        window.render(ResourceSnapshot(2, None, (), DiagnosticContext(), True))
        for label in window.values.values():
            self.assertEqual(label.get_text(), "—")
        window.close()
        settle(lambda: window.closed)
        self.assertTrue(window.closed)
        self.assertTrue(window.cancelled.is_set())
        self.assertIsNone(window._timer)
        self.assertIsNone(window._poll)

    def test_closing_during_a_sample_does_not_block_or_publish_late_result(self):
        started, released = Event(), Event()
        def sample(_context, cancelled):
            started.set()
            cancelled.wait(2)
            released.set()
            return ResourceSnapshot(0, None, (), DiagnosticContext(), True)
        sampler = Mock()
        sampler.sample.side_effect = sample
        window = DiagnosticsWindow(None, DiagnosticContext, lambda key: key, Mock(), sampler=sampler)
        self.addCleanup(window.destroy)
        settle(started.is_set)
        window.destroy()
        self.assertTrue(window.closed)
        self.assertTrue(released.wait(1))
        settle(seconds=0.15)
        self.assertEqual(len(window.history), 0)

    def test_history_updates_preserve_reading_and_selection_when_rows_expire(self):
        sampler = Mock()
        sampler.sample.return_value = ResourceSnapshot(0, None, (), DiagnosticContext(), True)
        window = DiagnosticsWindow(None, DiagnosticContext, translator("en"), Mock(), sampler=sampler)
        self.addCleanup(window.destroy)
        window.present()
        settle(lambda: window._future is None)
        GLib.source_remove(window._timer)
        window._timer = None
        window.history_expander.set_expanded(True)
        view = window.history_view
        buffer = view.get_buffer()
        panel = window.history_expander.get_child()

        def append(index):
            window.values["main", "cpu"].set_text(f"{index}%")
            window._record_history()

        def visible_line():
            start, _top = view.get_line_at_y(view.get_visible_rect().y)
            end = start.copy()
            end.forward_to_line_end()
            return buffer.get_text(start, end, False)

        def selected_text():
            bounds = buffer.get_selection_bounds()
            return buffer.get_text(bounds[-2], bounds[-1], False)

        for index in range(60):
            append(index)
        settle(seconds=0.2)
        start = buffer.get_start_iter()
        start.forward_lines(25)
        end = start.copy()
        end.forward_to_line_end()
        buffer.select_range(end, start)
        panel.get_vadjustment().set_value(200)
        settle(seconds=0.2)
        before_line, before_selection = visible_line(), selected_text()
        for index in range(60, 65):
            append(index)
            settle(seconds=0.05)
        self.assertEqual(visible_line(), before_line)
        self.assertEqual(selected_text(), before_selection)
        self.assertEqual(len(window.history), 60)

    def test_tool_reuses_one_independent_window_and_reopens_after_close(self):
        app = Gtk.Application(application_id="local.termia.DiagnosticsTest")
        app.register(None)
        tool = DiagnosticsTool(app.add_window, DiagnosticContext, Mock())
        self.addCleanup(tool.close)
        window = tool.show("es")
        self.assertIs(tool.show("es"), window)
        self.assertIsNone(window.get_transient_for())
        self.assertFalse(window.get_modal())
        window.close()
        settle(lambda: window.closed)
        replacement = tool.show("ca")
        self.assertIsNot(replacement, window)
        self.assertFalse(replacement.closed)
