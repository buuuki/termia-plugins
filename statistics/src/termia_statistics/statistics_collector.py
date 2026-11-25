# SPDX-FileCopyrightText: 2026 Jordi Pons
# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional aggregate statistics observer for terminal sessions."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from .models import StatisticsSettings


class StatisticsCollector:
    def __init__(
        self,
        statistics: Callable[[], StatisticsSettings],
        update: Callable[[StatisticsSettings], None],
        save: Callable[[], None],
    ) -> None:
        self.statistics = statistics
        self.save = save
        self.update = update
        self.run_connections = 0
        self._save_source: int | None = None

    def _schedule_save(self) -> None:
        if self._save_source is None:
            self._save_source = GLib.timeout_add_seconds(30, self._on_save_timeout)

    def _on_save_timeout(self) -> bool:
        self._save_source = None
        self.save()
        return GLib.SOURCE_REMOVE

    def connection_started(self, server_id: str) -> None:
        stats = self.statistics()
        stats.connections += 1
        stats.server_connections[server_id] = stats.server_connections.get(server_id, 0) + 1
        self.run_connections += 1
        self.update(stats)
        self._schedule_save()

    def duration_finished(self, duration: float) -> None:
        stats = self.statistics()
        stats.completed_sessions += 1
        stats.duration_total += duration
        stats.duration_min = duration if stats.duration_min is None else min(stats.duration_min, duration)
        stats.duration_max = max(stats.duration_max, duration)
        self.update(stats)
        self._schedule_save()

    def flush(self) -> None:
        if self._save_source is not None:
            self.save()
            GLib.source_remove(self._save_source)
            self._save_source = None
