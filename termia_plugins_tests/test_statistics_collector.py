import unittest
from unittest.mock import Mock, patch

from .statistics_plugin_support import plugin_module

collector_module = plugin_module("statistics_collector")
StatisticsSettings = plugin_module("models").StatisticsSettings


class StatisticsCollectorTests(unittest.TestCase):
    def test_coalesces_events_and_flushes_pending_data_once(self):
        stats = StatisticsSettings()
        update, save = Mock(), Mock()
        collector = collector_module.StatisticsCollector(lambda: stats, update, save)
        with patch.object(collector_module.GLib, "timeout_add_seconds", return_value=10) as timer, \
                patch.object(collector_module.GLib, "source_remove") as remove:
            collector.connection_started("synthetic")
            collector.duration_finished(6.0)
            collector.duration_finished(5.0)
            timer.assert_called_once_with(30, collector._on_save_timeout)
            collector.flush()
            collector.flush()
            remove.assert_called_once_with(10)
        save.assert_called_once_with()
        self.assertEqual(stats.server_connections, {"synthetic": 1})
        self.assertEqual((stats.connections, collector.run_connections), (1, 1))
        self.assertEqual((stats.completed_sessions, stats.duration_total), (2, 11))
        self.assertEqual((stats.duration_min, stats.duration_max), (5, 6))
