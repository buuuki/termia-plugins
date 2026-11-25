import unittest
from typing import get_type_hints

from .statistics_plugin_support import plugin_module

StatisticsPresenter = plugin_module("statistics_presenter").StatisticsPresenter
StatisticsDialog = plugin_module("statistics_view").StatisticsDialog


class StatisticsDialogTests(unittest.TestCase):
    def test_presenter_annotation_supports_runtime_introspection(self):
        self.assertIs(get_type_hints(StatisticsDialog.__init__)["presenter"], StatisticsPresenter)

    def test_accepts_only_explicit_view_dependencies(self) -> None:
        make_window = object()
        presenter = object()
        def translate(key):
            return key

        dialog = StatisticsDialog(make_window, presenter, translate)

        self.assertIs(dialog.make_window, make_window)
        self.assertIs(dialog.presenter, presenter)
        self.assertIs(dialog.translate, translate)
