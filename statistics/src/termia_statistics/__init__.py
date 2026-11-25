# SPDX-License-Identifier: GPL-3.0-or-later
from dataclasses import asdict
from weakref import WeakSet

from .dialog_window import DialogWindow
from .i18n import translator
from .models import Server, StatisticsSettings
from .statistics_collector import StatisticsCollector
from .statistics_presenter import StatisticsPresenter
from .statistics_view import StatisticsDialog

API_VERSION = 2


class StatisticsTool:
    def __init__(self, data, attach_window, apply_style):
        self.data = data
        self.attach_window = attach_window
        self.apply_style = apply_style
        self.windows = WeakSet()
        self.collector = StatisticsCollector(
            self.snapshot, lambda stats: data.update(asdict(stats)), data.flush,
        )

    def snapshot(self):
        return StatisticsSettings(**self.data.snapshot())

    def on_session_event(self, event, value):
        if event == "connection_started":
            self.collector.connection_started(value)
        elif event == "duration_finished":
            self.collector.duration_finished(value)
        elif event == "flush":
            self.collector.flush()

    def make_window(self, **kwargs):
        window = DialogWindow(apply_style=self.apply_style, **kwargs)
        self.attach_window(window)
        self.windows.add(window)
        return window

    def dialog(self, language):
        translate = translator(language)
        presenter = StatisticsPresenter(
            self.snapshot, lambda: [Server(**row) for row in self.data.servers()],
            lambda: self.collector.run_connections, translate,
        )
        return StatisticsDialog(self.make_window, presenter, translate)

    def show(self, language):
        self.dialog(language).show()

    def show_session(self, language, server_id):
        count = self.snapshot().server_connections.get(server_id, 0)
        self.dialog(language).show_session(count)

    def close(self):
        self.collector.flush()
        for window in list(self.windows):
            window.destroy()


def create(*, session_events, statistics_data, attach_window, apply_style):
    if session_events != 1:
        raise ValueError("Unsupported session event contract")
    return StatisticsTool(statistics_data, attach_window, apply_style)
