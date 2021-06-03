# __init__.py
# GPL v3

import subprocess, gi, os
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, GLib

from .main_container import MdMainContainer
from .prefs.prefs_dialog import MdConfigWidget
from .prefs.export_dialog import MdExportDialog
from .constants import MD_PREVIEW_KEY_BASE
from .utils import init_gettext

_ = init_gettext()

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

################################################################################

class MarkdownGeditPluginApp(GObject.Object, Gedit.AppActivatable):
	app = GObject.property(type=Gedit.App)

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		self.build_main_menu()

	def do_deactivate(self):
		self.remove_menu()

	def build_main_menu(self):
		self.menu_ext_tools = self.extend_menu('tools-section')
		self.menu_ext_view = self.extend_menu('view-section')
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menus.ui'))
		menu = builder.get_object('md-preview-actions')
		self.menu_section_actions = Gio.MenuItem.new_section(_("Markdown Preview"), menu)
		self.menu_ext_tools.append_menu_item(self.menu_section_actions)
		menu = builder.get_object('md-preview-settings')
		self.menu_section_settings = Gio.MenuItem.new_section(_("Markdown Preview"), menu)
		self.menu_ext_view.append_menu_item(self.menu_section_settings)
		menu = builder.get_object('md-preview-zoom')
		self.menu_section_zoom = Gio.MenuItem.new_submenu(_("Zoom"), menu)
		self.menu_ext_view.append_menu_item(self.menu_section_zoom)

	def remove_menu(self):
		self.menu_ext_tools = None # XXX ?
		self.menu_ext_view = None # XXX ?

	############################################################################
################################################################################

class MarkdownGeditPluginWindow(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable):
	window = GObject.property(type=Gedit.Window)

	def __init__(self):
		GObject.Object.__init__(self)
		self._auto_position = False # XXX
		self.preview = MdMainContainer(self)

	def do_activate(self):
		self._handlers = []
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		sig_id0 = self.window.connect('active-tab-changed', self.preview.on_file_changed)
		self._handlers.append(sig_id0)
		sig_id1 = self.window.connect('active-tab-state-changed', self.preview.on_file_changed)
		self._handlers.append(sig_id1)
		self.connect_actions()
		self.preview.do_activate()

	# This is called every time the gui is updated
	def do_update_state(self):
		self.preview.do_update_state()

	def do_deactivate(self):
		self.preview.do_deactivate()
		self.window.disconnect(self._handlers[0])
		self.window.disconnect(self._handlers[1])

	def add_action_simple(self, action_name, callback):
		new_action = Gio.SimpleAction(name=action_name)
		new_action.connect('activate', callback)
		self.window.add_action(new_action)

	def connect_actions(self):
		self.add_action_simple('md-prev-export-doc', self.export_doc)
		self.add_action_simple('md-prev-print-doc', self.preview.print_doc)

		self.add_action_simple('md-prev-zoom-in', self.on_zoom_in)
		self.add_action_simple('md-prev-zoom-original', self.on_zoom_original)
		self.add_action_simple('md-prev-zoom-out', self.on_zoom_out)

		self.add_action_simple('md-prev-next', self.preview.on_next_page)
		self.add_action_simple('md-prev-previous', self.preview.on_previous_page)

		self.add_action_simple('md-prev-options', self.on_open_prefs)
		self.add_action_simple('md-prev-reload', self.preview.on_reload)

		self.add_action_simple('md-prev-open-link-with', self.on_open_link_with)
		self.add_action_simple('md-prev-open-image-with', self.on_open_image_with)

		action_view_mode = Gio.SimpleAction().new_stateful('md-set-view-mode', \
		            GLib.VariantType.new('s'), GLib.Variant.new_string('whole'))
		action_view_mode.connect('change-state', self.preview.change_splitter_action)

		bool_autoreload = self._settings.get_boolean('auto-reload')
		self.preview.auto_reload = bool_autoreload
		action_autoreload = Gio.SimpleAction().new_stateful('md-prev-set-autoreload', \
		                        None, GLib.Variant.new_boolean(bool_autoreload))
		action_autoreload.connect('change-state', self.preview.on_set_reload)

		position = self._settings.get_string('position')
		self._auto_position = position == 'auto'
		action_panel = Gio.SimpleAction().new_stateful('md-prev-pane', \
		           GLib.VariantType.new('s'), GLib.Variant.new_string(position))
		action_panel.connect('change-state', self.on_change_panel_from_popover)

		self.window.add_action(action_view_mode)
		self.window.add_action(action_panel)
		self.window.add_action(action_autoreload)

	def on_change_panel_from_popover(self, *args):
		self._auto_position = False
		if GLib.Variant.new_string('side') == args[1]:
			self._settings.set_string('position', 'side')
			args[0].set_state(GLib.Variant.new_string('side'))
		elif GLib.Variant.new_string('bottom') == args[1]:
			self._settings.set_string('position', 'bottom')
			args[0].set_state(GLib.Variant.new_string('bottom'))
		else:
			self._auto_position = True
			self._settings.set_string('position', 'auto')
			args[0].set_state(GLib.Variant.new_string('auto'))

	############################################################################
	
	def do_create_configure_widget(self):
		# Just return a box, PeasGtk will automatically pack it into a dialog and show it.
		widget = MdConfigWidget(self.plugin_info.get_data_dir())
		return widget

	def on_open_prefs(self, *args):
		w = Gtk.Window(title=_("Markdown Preview"), default_height=350)
		widget = MdConfigWidget(self.plugin_info.get_data_dir())
		w.add(widget)
		w.present()
		w.show_all() # immonde mais reproduit le comportement de libpeas

	def export_doc(self, *args):
		dialog = MdExportDialog(self.preview.recognize_format(), self.window, self._settings)
		should_close = False
		while not should_close:
			response_id = dialog.run()
			if response_id == Gtk.ResponseType.OK:
				# If "next" has been clicked but the user changes their mind, or
				# if there was an error, the dialog should be re-run until the
				# user successfully exports their file (or gives up).
				should_close = dialog.do_next()
			else:
				should_close = True
		dialog.destroy()

	############################################################################
	# Actions directly tied to the webview #####################################

	def on_zoom_in(self, *args):
		self.preview._webview_manager.on_zoom_in()

	def on_zoom_original(self, *args):
		self.preview._webview_manager.on_zoom_original()

	def on_zoom_out(self, *args):
		self.preview._webview_manager.on_zoom_out()

	def on_open_link_with(self, *args):
		self.preview._webview_manager.on_open_link_with()

	def on_open_image_with(self, *args):
		self.preview._webview_manager.on_open_image_with()

	############################################################################
################################################################################
