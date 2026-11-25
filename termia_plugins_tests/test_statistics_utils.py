import unittest

from .statistics_plugin_support import plugin_module

Server = plugin_module("models").Server
StatisticsSettings = plugin_module("models").StatisticsSettings
average_session_duration = plugin_module("statistics_utils").average_session_duration
format_duration = plugin_module("statistics_utils").format_duration
top_server_statistics = plugin_module("statistics_utils").top_server_statistics


class StatisticsUtilsTests(unittest.TestCase):
    def test_average_duration(self) -> None:
        self.assertIsNone(average_session_duration(StatisticsSettings()))
        self.assertEqual(average_session_duration(StatisticsSettings(completed_sessions=2, duration_total=9)), 4.5)

    def test_format_duration_clamps_negative_values(self) -> None:
        self.assertEqual(format_duration(None), "--:--:--")
        self.assertEqual(format_duration(-1), "00:00:00")
        self.assertEqual(format_duration(3661.9), "01:01:01")

    def test_top_servers_include_fallback_for_deleted_servers(self) -> None:
        stats = StatisticsSettings(server_connections={"missing": 5, "known": 3})
        servers = [Server(id="known", name="Web", host="example.test", user="admin", port=2200)]

        rows = top_server_statistics(stats, servers)

        self.assertEqual(rows[0].name, "missing")
        self.assertEqual(rows[0].subtitle, "")
        self.assertEqual(rows[1].subtitle, "admin@example.test:2200")
