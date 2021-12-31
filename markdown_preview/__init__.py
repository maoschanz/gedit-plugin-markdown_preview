# __init__.py
# GPL v3

import subprocess, gi, os
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, GLib

from .main_container import MdMainContainer
from .tags_manager import MdTagsManager
from .prefs.prefs_dialog import MdConfigWidget
from .prefs.export_assistant import MdExportAssistant
from .constants import KeyboardShortcuts, MD_PREVIEW_KEY_BASE
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
		self.add_all_accelerators()

	def do_deactivate(self):
		self.remove_menu()
		self.remove_accelerators()

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

	def add_all_accelerators(self):
		self._kb_settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE + '.keybindings')
		for i in range(len(KeyboardShortcuts.SettingsKeys)):
			self.add_one_accelerator(KeyboardShortcuts.SettingsKeys[i], \
			                                  KeyboardShortcuts.ActionsNames[i])

	def add_one_accelerator(self, setting_key, action_name):
		accels = self._kb_settings.get_strv(setting_key)
		if len(accels) > 0:
			self.app.add_accelerator(accels[0], action_name, None)

	def remove_accelerators(self):
		for i in range(len(KeyboardShortcuts.SettingsKeys)):
			self.app.remove_accelerator(KeyboardShortcuts.SettingsKeys[i], None)

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

		action_view_mode = Gio.SimpleAction().new_stateful( \
			'md-set-view-mode', \
			GLib.VariantType.new('s'), \
			GLib.Variant.new_string(self._settings.get_string('splitter')) \
		)
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

		########################################################################

		action_remove = Gio.SimpleAction(name='md-prev-remove-all')
		action_remove.connect('activate', lambda i, j: self.view_method('remove_all'))

		self.add_format_action('md-prev-format-title-upper', 'remove_block', '#')
		self.add_format_action('md-prev-format-title-lower', 'format_block', '#')

		self.add_format_action('md-prev-format-bold', 'format_inline', '**')
		self.add_format_action('md-prev-format-italic', 'format_inline', '*')
		self.add_format_action('md-prev-format-underline', 'format_inline', '__')
		self.add_format_action('md-prev-format-stroke', 'format_inline', '~~')
		self.add_format_action('md-prev-format-monospace', 'format_inline', '`')

		self.add_format_action('md-prev-block-code', 'format_block2', '\n```\n')
		self.add_format_action('md-prev-block-quote', 'format_block', '>')
		self.add_format_action('md-prev-list-unordered', 'format_block', '-')
		self.add_format_action('md-prev-list-ordered', 'format_block', '1.')

		self.add_format_action('md-prev-insert-picture', 'insert_picture')
		self.add_format_action('md-prev-insert-link', 'insert_link')
		self.add_format_action('md-prev-insert-table-2', 'insert_table', 2)
		self.add_format_action('md-prev-insert-table-3', 'insert_table', 3)
		self.add_format_action('md-prev-insert-table-4', 'insert_table', 4)
		self.add_format_action('md-prev-insert-table-5', 'insert_table', 5)

	def add_format_action(self, action_name, method, arg=None):
		action = Gio.SimpleAction(name=action_name)
		action.connect('activate', lambda i, j: self.view_method(method, arg))
		self.window.add_action(action)

	def view_method(self, method_name, argument=None):
		if self.preview.recognize_format() != 'md':
			return

		view = self.window.get_active_view()
		if view and view.markdown_preview_view_activatable:
			v = view.markdown_preview_view_activatable.tags_manager
		else:
			return

		if method_name == 'insert_table':
			v.insert_table(argument)
		elif method_name == 'insert_picture':
			v.insert_picture(self.window)
		elif method_name == 'insert_link':
			v.insert_link(self.window)

		elif method_name == 'format_inline':
			v.add_word_tags(argument)

		elif method_name == 'format_block':
			v.add_line_tags(argument)
		elif method_name == 'format_block2':
			v.add_block_tags(argument, argument)
		elif method_name == 'remove_block':
			v.remove_line_tags(argument)

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
		ass = MdExportAssistant(self.preview, self.window, self._settings)
		ass.present()

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

class MarkdownGeditPluginView(GObject.Object, Gedit.ViewActivatable):
	view = GObject.Property(type=Gedit.View)

	def __init__(self):
		self.popup_handler_id = 0
		GObject.Object.__init__(self)

	def do_activate(self):
		self.view.markdown_preview_view_activatable = self
		model_path = os.path.join(BASE_PATH, 'view-menu.ui')
		self.menu_builder = Gtk.Builder().new_from_file(model_path)
		self.popup_handler_id = self.view.connect('populate-popup', self.populate_popup)
		self.tags_manager = MdTagsManager(self)

	def do_deactivate(self):
		if self.popup_handler_id != 0:
			self.view.disconnect(self.popup_handler_id)
			self.popup_handler_id = 0
		delattr(self.view, 'markdown_preview_view_activatable')

	def populate_popup(self, view, popup):
		if not isinstance(popup, Gtk.MenuShell):
			return

		item = Gtk.SeparatorMenuItem()
		item.show()
		popup.append(item)

		item = Gtk.MenuItem(_("Markdown tags"))
		menu = Gtk.Menu().new_from_model(self.menu_builder.get_object('right-click-menu'))
		item.set_submenu(menu)
		item.show()
		if self.recognize_format() != 'md':
			item.set_sensitive(False)
		popup.append(item)

	def recognize_format(self): # TODO doc.get_language() ? pourquoi j'appelle
		# le recognize_format depuis ce fichier à d'autres endroits ?
		doc = self.view.get_buffer()
		name = doc.get_short_name_for_display()
		temp = name.split('.')[-1].lower()
		if temp == 'md':
			return 'md'
		elif temp == 'html':
			return 'html'
		return 'error'

	############################################################################
################################################################################

