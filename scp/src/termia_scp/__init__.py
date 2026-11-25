# SPDX-License-Identifier: GPL-3.0-or-later
"""Contextual SCP upload UI for Termia external API 2."""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .i18n import translator

API_VERSION = 2


class UploadUI:
    def __init__(self, language):
        self.translate = translator(language)

    def select_files(self):
        chooser = Gtk.FileChooserNative(
            title=self.translate("send_files_to_server"),
            action=Gtk.FileChooserAction.OPEN,
            modal=True,
        )
        chooser.set_select_multiple(True)
        return chooser

    def destination(self, dialog, add_button, default_destination):
        dialog.set_resizable(False)
        dialog.set_default_size(460, -1)
        add_button(dialog, self.translate("cancel"), Gtk.ResponseType.CANCEL)
        add_button(
            dialog,
            self.translate("send_files_to_server_destination_confirm"),
            Gtk.ResponseType.OK,
        )
        dialog.set_default_response(Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_spacing(8)
        label = Gtk.Label(label=self.translate("send_files_to_server_destination_label"))
        label.set_xalign(0)
        entry = Gtk.Entry()
        entry.set_text(default_destination)
        entry.set_activates_default(True)
        error = Gtk.Label(label="")
        error.set_xalign(0)
        error.set_wrap(True)
        error.add_css_class("error")
        error.set_visible(False)
        content.append(label)
        content.append(entry)
        content.append(error)

        return entry, error

    def progress(self, dialog, add_button, name, destination, file_list):
        dialog.set_resizable(False)
        dialog.set_default_size(460, -1)
        cancel = add_button(dialog, self.translate("cancel"), Gtk.ResponseType.CANCEL)

        content = dialog.get_content_area()
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.set_spacing(12)
        target = Gtk.Label(label=self.translate("send_files_to_server_running").format(name=name, destination=destination))
        target.set_xalign(0)
        target.set_wrap(True)
        files = Gtk.Label(label=file_list)
        files.set_xalign(0)
        files.set_wrap(True)
        files.add_css_class("dim-label")
        progress = Gtk.ProgressBar()
        progress.pulse()
        status = Gtk.Label(label="")
        status.set_xalign(0)
        status.set_wrap(True)
        status.add_css_class("dim-label")
        content.append(target)
        content.append(files)
        content.append(progress)
        content.append(status)

        return cancel, progress, status


class SCPTool:
    def show(self, language):
        return UploadUI(language)

    def close(self):
        # Termia owns operation windows and cancels transfers on deactivation.
        pass


def create(*, scp_upload_ui):
    if scp_upload_ui != 1:
        raise ValueError("Unsupported SCP UI contract")
    return SCPTool()
