import subprocess, gi, os, markdown
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, WebKit2, GLib

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

from .prefs import MdConfigWidget
from .preview import MdPreviewBar
from .export import MdExportDialog

try:
	import gettext
	gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
	gettext.textdomain('gedit-plugin-markdown-preview')
	_ = gettext.gettext
except:
	_ = lambda s: s

MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'

####### ####### #######

class MarkdownGeditPluginApp(GObject.Object, Gedit.AppActivatable):
	app = GObject.property(type=Gedit.App)

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		self.build_main_menu()
		self.add_accelerators()

	def do_deactivate(self):
		self.remove_menu()
		self.remove_accelerators()

	def build_main_menu(self):
		self.menu_ext_tools = self.extend_menu('tools-section')
		self.menu_ext_view = self.extend_menu('view-section')
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menus.ui'))
#		menu = builder.get_object('md-preview-menu')
#		self.menu_section = Gio.MenuItem.new_submenu(_("Markdown Preview"), menu)
#		self.menu_ext.append_menu_item(self.menu_section)

		# Show the zoom settings as a submenu here because it's ugly otherwise
#		menu = builder.get_object('md-preview-actions')
#		self.menu_section_actions = Gio.MenuItem.new_section(_("Markdown Preview"), menu)
#		self.menu_ext.append_menu_item(self.menu_section_actions)
#		menu = builder.get_object('md-preview-zoom')
#		self.menu_section_zoom = Gio.MenuItem.new_submenu(_("Zoom"), menu)
#		self.menu_ext.append_menu_item(self.menu_section_zoom)
#		menu = builder.get_object('md-preview-settings')
#		self.menu_section_settings = Gio.MenuItem.new_section(None, menu)
#		self.menu_ext.append_menu_item(self.menu_section_settings)

		# Show the zoom settings as a submenu here because it's ugly otherwise
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
		self.menu_ext_tools = None # FIXME ?
		self.menu_ext_view = None # FIXME ?

	def add_accelerators(self):
		self.app.add_accelerator("<Primary>E", "win.md-prev-insert-picture", None)
#		self.app.add_accelerator("<Primary><Shift>M", "win.uncomment", None)
		return

	def remove_accelerators(self):
		self.app.remove_accelerator("win.md-prev-insert-picture", None)
#		self.app.remove_accelerator("win.uncomment", None)
		return

####### ####### #######

class MarkdownGeditPluginWindow(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable):
	window = GObject.property(type=Gedit.Window)

	def __init__(self):
		GObject.Object.__init__(self)
		self.preview = MdPreviewBar(self)

	def do_activate(self):
		self._handlers = []
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self.connect_actions()
		self.preview.do_activate()

	# This is called every time the gui is updated
	def do_update_state(self):
		self.preview.do_update_state()

	def do_deactivate(self):
		self.preview.do_deactivate()

	def connect_actions(self):
		action_export = Gio.SimpleAction(name='md-prev-export-doc')
		action_print = Gio.SimpleAction(name='md-prev-print-doc')
		action_export.connect('activate', self.export_doc)
		action_print.connect('activate', self.print_doc)
		
		self.window.add_action(action_export)
		self.window.add_action(action_print)

		action_zoom_in = Gio.SimpleAction(name='md-prev-zoom-in')
		action_zoom_original = Gio.SimpleAction(name='md-prev-zoom-original')
		action_zoom_out = Gio.SimpleAction(name='md-prev-zoom-out')
		action_zoom_in.connect('activate', self.preview.on_zoom_in)
		action_zoom_original.connect('activate', self.preview.on_zoom_original)
		action_zoom_out.connect('activate', self.preview.on_zoom_out)
		
		self.window.add_action(action_zoom_in)
		self.window.add_action(action_zoom_original)
		self.window.add_action(action_zoom_out)

		action_paginated = Gio.SimpleAction().new_stateful('md-prev-set-paginated', \
		None, GLib.Variant.new_boolean(False))
		action_paginated.connect('change-state', self.preview.on_set_paginated)
		
		action_next = Gio.SimpleAction(name='md-prev-next')
		action_next.connect('activate', self.preview.on_next_page)
		
		action_previous = Gio.SimpleAction(name='md-prev-previous')
		action_previous.connect('activate', self.preview.on_previous_page)

		action_autoreload = Gio.SimpleAction().new_stateful('md-prev-set-autoreload', \
		None, GLib.Variant.new_boolean(self.preview.auto_reload))
		action_autoreload.connect('change-state', self.preview.on_set_reload)
		
		self.action_reload_preview = Gio.SimpleAction(name='md-prev-reload')
		self.action_reload_preview.connect('activate', self.preview.on_reload)

		action_panel = Gio.SimpleAction().new_stateful('md-prev-panel', \
		GLib.VariantType.new('s'), GLib.Variant.new_string(self._settings.get_string('position')))
		action_panel.connect('change-state', self.preview.on_change_panel_from_popover)

		action_presentation = Gio.SimpleAction(name='md-prev-presentation')
		action_presentation.connect('activate', self.preview.on_presentation)

		action_hide = Gio.SimpleAction(name='md-prev-hide')
		action_hide.connect('activate', self.preview.on_hide_panel)
		
		self.window.add_action(action_paginated)
		self.window.add_action(action_next)
		self.window.add_action(action_previous)
		self.window.add_action(action_panel)
		self.window.add_action(action_presentation)
		self.window.add_action(action_hide)
		self.window.add_action(action_autoreload)
		self.window.add_action(self.action_reload_preview)
		
		#-------------------------
		
		action_bold = Gio.SimpleAction(name='md-prev-format-bold')
		action_bold.connect('activate', lambda i, j: self.view_method('format_bold'))
		action_italic = Gio.SimpleAction(name='md-prev-format-italic')
		action_italic.connect('activate', lambda i, j: self.view_method('format_italic'))
		action_underline = Gio.SimpleAction(name='md-prev-format-underline')
		action_underline.connect('activate', lambda i, j: self.view_method('format_underline'))
		action_monospace = Gio.SimpleAction(name='md-prev-format-monospace')
		action_monospace.connect('activate', lambda i, j: self.view_method('format_monospace'))
		action_stroke = Gio.SimpleAction(name='md-prev-format-stroke')
		action_stroke.connect('activate', lambda i, j: self.view_method('format_stroke'))
		# TODO
		action_picture = Gio.SimpleAction(name='md-prev-insert-picture')
		action_picture.connect('activate', lambda i, j: self.view_method('insert_picture'))
		action_table = Gio.SimpleAction(name='md-prev-insert-table')
		action_table.connect('activate', lambda i, j: self.view_method('insert_table'))
		
		self.window.add_action(action_bold)
		self.window.add_action(action_italic)
		self.window.add_action(action_underline)
		self.window.add_action(action_monospace)
		self.window.add_action(action_stroke)
		# TODO
		self.window.add_action(action_picture)
		self.window.add_action(action_table)
	
	def view_method(self, name):
		if self.recognize_format() != 'md':
			return

		view = self.window.get_active_view()
		if view and view.markdown_preview_view_activatable:
			v = view.markdown_preview_view_activatable
		else:
			return
			
		print('action : ' + name)
		
		if name == 'insert_table':
			v.insert_table()
		elif name == 'insert_picture':
			v.insert_picture(self.window)
		elif name == 'format_bold':
			v.format_bold()
		elif name == 'format_italic':
			v.format_italic()
		elif name == 'format_monospace':
			v.format_monospace()
		elif name == 'format_stroke':
			v.format_stroke()
		elif name == 'format_underline':
			v.format_underline()
		# TODO
	
	# XXX virer ou renommer ça
	def recognize_format(self):
		doc = self.window.get_active_document()
		# It will not load documents which are not .md/.html/.tex
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		self.preview.display_warning(False, '')
		if temp[len(temp)-1] == 'md':
			return 'md'
		elif temp[len(temp)-1] == 'html':
#			self.window.lookup_action('md-prev-insert-picture').set_enabled(False)
			return 'html'
		elif temp[len(temp)-1] == 'tex':
#			self.window.lookup_action('md-prev-insert-picture').set_enabled(False)
			return 'tex'
		# The current content is not replaced, which allows document consulation while working on a file
		self.window.lookup_action('md-prev-export-doc').set_enabled(False)
		self.window.lookup_action('md-prev-print-doc').set_enabled(False)
#		self.window.lookup_action('md-prev-insert-picture').set_enabled(False)
		if doc.is_untitled():
			self.preview.display_warning(True, _("Can't preview an unsaved document"))
		else:
			self.preview.display_warning(True, _("Unsupported type of document: ") + name)
		return 'error'

	def on_change_panel_from_popover(self, *args):
		if GLib.Variant.new_string('side') == args[1]:
			self._settings.set_string('position', 'side')
			args[0].set_state(GLib.Variant.new_string('side'))
		else:
			self._settings.set_string('position', 'bottom')
			args[0].set_state(GLib.Variant.new_string('bottom'))

	def on_hide_panel(self, *args):
		if self._settings.get_string('position') == 'bottom':
			self.window.get_bottom_panel().set_property('visible', False)
		else:
			self.window.get_side_panel().set_property('visible', False)

	def show_on_panel(self):
		# Get the bottom bar (A Gtk.Stack), or the side bar, and add our bar to it.
		if self._settings.get_string('position') == 'bottom':
			self.panel = self.window.get_bottom_panel()
			self.preview_bar.props.orientation = Gtk.Orientation.HORIZONTAL
			self.buttons_main_box.props.orientation = Gtk.Orientation.VERTICAL
		else:
			self.panel = self.window.get_side_panel()
			self.preview_bar.props.orientation = Gtk.Orientation.VERTICAL
			self.buttons_main_box.props.orientation = Gtk.Orientation.HORIZONTAL
		self.panel.add_titled(self.preview_bar, 'markdown_preview', _("Markdown Preview"))
		self.panel.set_visible_child(self.preview_bar)
		self.preview_bar.show_all()
		self.pages_box.props.visible = self.is_paginated
		if self.window.get_state() is 'STATE_NORMAL':
			self.on_reload()

	def remove_from_panel(self):
		if self.panel is not None:
			self.panel.remove(self.preview_bar)

	########
	
	def change_panel(self, *args):
		self.remove_from_panel()
		self.show_on_panel()
		self.do_update_state()
		self.on_reload()

	def do_create_configure_widget(self):
		# Just return your box, PeasGtk will automatically pack it into a dialog and show it.
		widget = MdConfigWidget(self.plugin_info.get_data_dir())
		return widget

	def export_doc(self, *args):
		dialog = MdExportDialog(self.recognize_format(), self.window, self._settings)
		response_id = dialog.run()
		if response_id == Gtk.ResponseType.CANCEL:
			dialog.do_cancel_export()
		elif response_id == Gtk.ResponseType.OK:
			dialog.do_next()

	def print_doc(self, *args):
		p = WebKit2.PrintOperation.new(self.preview._webview)
		p.run_dialog()

####### ####### #######

class MarkdownGeditPluginView(GObject.Object, Gedit.ViewActivatable):
	view = GObject.Property(type=Gedit.View)

	def __init__(self):
		self.popup_handler_id = 0
		GObject.Object.__init__(self)

	def do_activate(self):
		self.view.markdown_preview_view_activatable = self
		self.menu_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menus.ui'))
		self.popup_handler_id = self.view.connect('populate-popup', self.populate_popup)

	def do_deactivate(self):
		if self.popup_handler_id != 0:
			self.view.disconnect(self.popup_handler_id)
			self.popup_handler_id = 0
		delattr(self.view, "markdown_preview_view_activatable")

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
	
	def recognize_format(self):
		doc = self.view.get_buffer()
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		if temp[len(temp)-1] == 'md':
			return 'md'
		elif temp[len(temp)-1] == 'html':
			return 'html'
		elif temp[len(temp)-1] == 'tex':
			return 'tex'
		return 'error'
		
	################
	
	def format_bold(self):
		pass
	
	def format_italic(self):
		pass
	
	def format_monospace(self):
		pass
	
	def format_stroke(self):
		pass
	
	def format_underline(self):
		pass
	
	def insert_picture(self, window):
		# Building a FileChooserDialog for pictures
		file_chooser = Gtk.FileChooserDialog(_("Select a picture"), window,
			Gtk.FileChooserAction.OPEN,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		onlyPictures = Gtk.FileFilter()
		onlyPictures.set_name("Pictures")
		onlyPictures.add_mime_type('image/*')
		file_chooser.set_filter(onlyPictures)
		response = file_chooser.run()

		# It gets the chosen file's path
		if response == Gtk.ResponseType.OK:
			doc = self.view.get_buffer()
			picture_path = '![](' + file_chooser.get_filename() + ')'
			iter = doc.get_iter_at_mark(doc.get_insert())
			doc.insert(iter, picture_path)
		file_chooser.destroy()
		
	def insert_table(self):
		doc = self.view.get_buffer()
		table = '|||\n|--|--|\n|||'
		iter = doc.get_iter_at_mark(doc.get_insert())
		doc.insert(iter, table)

##################################################
