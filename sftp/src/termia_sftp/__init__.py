# SPDX-License-Identifier: GPL-3.0-or-later
from .i18n import translator
from .view import SFTPWindow

API_VERSION = 2


class ExplorerTool:
    def show(self, language):
        translate = translator(language)

        def open_view(parent, connection, title, host_translate, on_closed, owner_id):
            def label(key):
                value = translate(key)
                return host_translate(key) if value == key else value

            return SFTPWindow(parent, connection, title, label, on_closed, owner_id)

        return open_view

    def close(self):
        pass


def create(*, sftp_explorer):
    if sftp_explorer != 1:
        raise ValueError("Unsupported SFTP explorer capability")
    return ExplorerTool()
