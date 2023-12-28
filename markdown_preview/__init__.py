# __init__.py
# GPL v3

import subprocess, gi, os
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, GLib

from .main_container import MdMainContainer
from .tags_manager import MdTagsManager
from .prefs.prefs_dialog import MdConfigWidget
from .prefs.export_assistant import MdExportAssistant
from .constants import KEYBOARD_SHORTCUTS, MD_PREVIEW_KEY_BASE
from .utils import init_gettext, recognize_format

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
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menus.ui'))

		# Append a section to the primary menu's "tools" submenu
		self.menu_ext_tools = self.extend_menu('tools-section')
		menu = builder.get_object('md-preview-actions')
		self.menu_section_actions = Gio.MenuItem.new_section(_("Markdown Preview"), menu)
		self.menu_ext_tools.append_menu_item(self.menu_section_actions)

		# Append two sections to the primary menu's "view" submenu
		self.menu_ext_view = self.extend_menu('view-section')
		menu = builder.get_object('md-preview-settings')
		menu_section_settings = Gio.MenuItem.new_section(_("Markdown Preview"), menu)
		self.menu_ext_view.append_menu_item(menu_section_settings)
		menu = builder.get_object('md-preview-zoom')
		self.menu_section_zoom = Gio.MenuItem.new_submenu(_("Zoom"), menu)
		self.menu_ext_view.append_menu_item(self.menu_section_zoom)

	def remove_menu(self):
		self.menu_ext_tools = None
		self.menu_ext_view = None

	def add_all_accelerators(self):
		self._kb_settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE + '.keybindings')
		for editing_action_id, label in KEYBOARD_SHORTCUTS.items():
			self.add_one_accelerator(editing_action_id)

	def add_one_accelerator(self, editing_action_id):
		action_name = 'win.md-prev-editing-' + editing_action_id
		accels = self._kb_settings.get_strv(editing_action_id)
		if len(accels) > 0:
			self.app.add_accelerator(accels[0], action_name, None)

	def remove_accelerators(self):
		for editing_action_id, label in KEYBOARD_SHORTCUTS.items():
			action_name = 'win.md-prev-editing-' + editing_action_id
			self.app.remove_accelerator(action_name, None)

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

		self._connect_handler(self.window, 'active-tab-changed')
		self._connect_handler(self.window, 'active-tab-state-changed')
		self._connect_handler(self.window.get_bottom_panel(), 'notify::visible-child')
		self._connect_handler(self.window.get_side_panel(), 'notify::visible-child')

		self.connect_actions()
		self.preview.do_activate()

	def _connect_handler(self, widget, signal_name):
		sig_id = widget.connect(signal_name, self.preview.on_file_changed)
		self._handlers.append(sig_id)

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

		# action_remove = Gio.SimpleAction(name='md-prev-remove-all')
		# action_remove.connect('activate', lambda i, j: self.method_from_view('remove_all'))
		# TODO ^ v4

		self.add_format_action('md-prev-editing-title-1', 'format_lines', '#')
		self.add_format_action('md-prev-editing-title-2', 'format_lines', '##')
		self.add_format_action('md-prev-editing-title-3', 'format_lines', '###')
		self.add_format_action('md-prev-editing-title-4', 'format_lines', '####')
		self.add_format_action('md-prev-editing-title-5', 'format_lines', '#####')
		self.add_format_action('md-prev-editing-title-6', 'format_lines', '#######')

		self.add_format_action('md-prev-editing-bold', 'format_inline', '**')
		self.add_format_action('md-prev-editing-italic', 'format_inline', '*')
		self.add_format_action('md-prev-editing-underline', 'format_inline', '__')
		self.add_format_action('md-prev-editing-stroke', 'format_inline', '~~')
		self.add_format_action('md-prev-editing-monospace', 'format_inline', '`')

		self.add_format_action('md-prev-editing-code-block', 'format_block', '```')
		self.add_format_action('md-prev-editing-quote', 'format_lines', '>')
		self.add_format_action('md-prev-editing-list-unordered', 'format_lines', '-')
		self.add_format_action('md-prev-editing-list-ordered', 'format_lines', '1.')

		self.add_format_action('md-prev-editing-insert-picture', 'insert_picture')
		self.add_format_action('md-prev-editing-insert-link', 'insert_link')
		self.add_format_action('md-prev-editing-insert-table-2', 'insert_table', 2)
		self.add_format_action('md-prev-editing-insert-table-3', 'insert_table', 3)
		self.add_format_action('md-prev-editing-insert-table-4', 'insert_table', 4)
		self.add_format_action('md-prev-editing-insert-table-5', 'insert_table', 5)

	def add_format_action(self, action_name, method, arg=None):
		action = Gio.SimpleAction(name=action_name)
		action.connect('activate', lambda i, j: self.method_from_view(method, arg))
		self.window.add_action(action)

	def method_from_view(self, method_name, argument=None):
		view = self.window.get_active_view()
		if view and view.markdown_preview_view_activatable:
			tags_manager = view.markdown_preview_view_activatable.tags_manager
		else:
			return
		if recognize_format(view.get_buffer()) != 'md':
			return
		# print('action : ' + method_name)

		if method_name == 'insert_table':
			tags_manager.insert_table(argument)
		elif method_name == 'insert_picture':
			tags_manager.insert_picture(self.window)
		elif method_name == 'insert_link':
			tags_manager.insert_link(self.window)

		elif method_name == 'format_inline':
			tags_manager.add_word_tags(argument)

		elif method_name == 'format_lines':
			tags_manager.add_line_tags(argument)
		elif method_name == 'format_block':
			tags_manager.add_block_tags(argument)
		elif method_name == 'remove_block':
			tags_manager.remove_line_tags(argument) # TODO

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
		if recognize_format(self.view.get_buffer()) != 'md':
			item.set_sensitive(False)
		popup.append(item)

	############################################################################
################################################################################

