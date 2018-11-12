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

	def add_accelerators(self):
		self.app.add_accelerator("<Primary>E", "win.md-prev-insert-picture", None)
		self.app.add_accelerator("<Primary>B", "win.md-prev-format-bold", None) # FIXME ?????
#		self.app.add_accelerator("<Primary><Shift>M", "win.uncomment", None)
		return

	def remove_accelerators(self):
		self.app.remove_accelerator("win.md-prev-insert-picture", None)
		self.app.remove_accelerator("win.md-prev-format-bold", None)
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
		self._handlers.append( self.window.connect('active-tab-changed', self.on_file_changed) )
		self.connect_actions()
		self.preview.do_activate()

	# This is called every time the gui is updated
	def do_update_state(self):
		self.preview.do_update_state()

	def do_deactivate(self):
		self.preview.do_deactivate()
		self.window.disconnect(self._handlers[0])

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

		autoreload = self._settings.get_boolean('auto-reload')
		self.preview.auto_reload = autoreload
		action_autoreload = Gio.SimpleAction().new_stateful('md-prev-set-autoreload', \
		None, GLib.Variant.new_boolean(autoreload))
		action_autoreload.connect('change-state', self.preview.on_set_reload)
		
		self.action_reload_preview = Gio.SimpleAction(name='md-prev-reload')
		self.action_reload_preview.connect('activate', self.preview.on_reload)

		action_panel = Gio.SimpleAction().new_stateful('md-prev-panel', \
		GLib.VariantType.new('s'), GLib.Variant.new_string(self._settings.get_string('position')))
		action_panel.connect('change-state', self.on_change_panel_from_popover)

		action_presentation = Gio.SimpleAction(name='md-prev-presentation')
		action_presentation.connect('activate', self.preview.on_presentation)

		action_hide = Gio.SimpleAction(name='md-prev-hide')
		action_hide.connect('activate', self.on_hide_panel)
		
		self.window.add_action(action_paginated)
		self.window.add_action(action_next)
		self.window.add_action(action_previous)
		self.window.add_action(action_panel)
		self.window.add_action(action_presentation)
		self.window.add_action(action_hide)
		self.window.add_action(action_autoreload)
		self.window.add_action(self.action_reload_preview)
		
		#-------------------------
		
		action_remove = Gio.SimpleAction(name='md-prev-remove-all')
		action_remove.connect('activate', lambda i, j: self.view_method('remove_all'))
		
		action_title_1 = Gio.SimpleAction(name='md-prev-format-title-1')
		action_title_1.connect('activate', lambda i, j: self.view_method('format_title_1'))
		action_title_2 = Gio.SimpleAction(name='md-prev-format-title-2')
		action_title_2.connect('activate', lambda i, j: self.view_method('format_title_2'))
		action_title_3 = Gio.SimpleAction(name='md-prev-format-title-3')
		action_title_3.connect('activate', lambda i, j: self.view_method('format_title_3'))
		action_title_4 = Gio.SimpleAction(name='md-prev-format-title-4')
		action_title_4.connect('activate', lambda i, j: self.view_method('format_title_4'))
		action_title_5 = Gio.SimpleAction(name='md-prev-format-title-5')
		action_title_5.connect('activate', lambda i, j: self.view_method('format_title_5'))
		action_title_6 = Gio.SimpleAction(name='md-prev-format-title-6')
		action_title_6.connect('activate', lambda i, j: self.view_method('format_title_6'))
		
		action_bold = Gio.SimpleAction(name='md-prev-format-bold')
		action_bold.connect('activate', lambda i, j: self.view_method('format_bold'))
		action_italic = Gio.SimpleAction(name='md-prev-format-italic')
		action_italic.connect('activate', lambda i, j: self.view_method('format_italic'))
		action_underline = Gio.SimpleAction(name='md-prev-format-underline')
		action_underline.connect('activate', lambda i, j: self.view_method('format_underline'))
		action_monospace = Gio.SimpleAction(name='md-prev-format-monospace')
		action_monospace.connect('activate', lambda i, j: self.view_method('format_monospace'))
		action_quote = Gio.SimpleAction(name='md-prev-format-quote')
		action_quote.connect('activate', lambda i, j: self.view_method('format_quote'))
		
		action_unordered = Gio.SimpleAction(name='md-prev-list-unordered')
		action_unordered.connect('activate', lambda i, j: self.view_method('list_unordered'))
		action_ordered = Gio.SimpleAction(name='md-prev-list-ordered')
		action_ordered.connect('activate', lambda i, j: self.view_method('list_ordered'))
		
		action_picture = Gio.SimpleAction(name='md-prev-insert-picture')
		action_picture.connect('activate', lambda i, j: self.view_method('insert_picture'))
		action_link = Gio.SimpleAction(name='md-prev-list-ordered')
		action_link.connect('activate', lambda i, j: self.view_method('insert_link'))
		action_table = Gio.SimpleAction(name='md-prev-insert-table')
		action_table.connect('activate', lambda i, j: self.view_method('insert_table'))
		
		self.window.add_action(action_remove)
		self.window.add_action(action_bold)
		self.window.add_action(action_italic)
		self.window.add_action(action_underline)
		self.window.add_action(action_monospace)
		self.window.add_action(action_quote)
		self.window.add_action(action_unordered)
		self.window.add_action(action_ordered)
		self.window.add_action(action_title_1)
		self.window.add_action(action_title_2)
		self.window.add_action(action_title_3)
		self.window.add_action(action_title_4)
		self.window.add_action(action_title_5)
		self.window.add_action(action_title_6)
		self.window.add_action(action_picture)
		self.window.add_action(action_link)
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
		elif name == 'insert_link':
			v.insert_link(self.window)
			
		elif name == 'format_bold':
			v.format_bold()
		elif name == 'format_italic':
			v.format_italic()
		elif name == 'format_monospace':
			v.format_monospace()
		elif name == 'format_quote':
			v.format_quote()
		elif name == 'format_underline':
			v.format_underline()
			
		elif name == 'list_ordered':
			v.list_ordered()
		elif name == 'list_unordered':
			v.list_unordered()
			
		elif name == 'format_title_1':
			v.format_title(1)
		elif name == 'format_title_2':
			v.format_title(2)
		elif name == 'format_title_3':
			v.format_title(3)
		elif name == 'format_title_4':
			v.format_title(4)
		elif name == 'format_title_5':
			v.format_title(5)
		elif name == 'format_title_6':
			v.format_title(6)

	def on_file_changed(self, *args):
		self.preview.file_format = self.recognize_format()
		self.preview.on_reload()
	
	def recognize_format(self):
		doc = self.window.get_active_document()
		# It will not load documents which are not .md/.html/.tex
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		self.preview.display_warning(False, '')
		if temp[len(temp)-1] == 'md':
			return 'md'
		elif temp[len(temp)-1] == 'html':
			return 'html'
		elif temp[len(temp)-1] == 'tex':
			return 'tex'
		if doc.is_untitled():
			self.preview.display_warning(True, _("Can't preview an unsaved document")) # FIXME
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

	########
	
	def do_create_configure_widget(self):
		# Just return a box, PeasGtk will automatically pack it into a dialog and show it.
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
	
	def recognize_format(self): # FIXME doc.get_language()
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
	
	def add_block_tags(self, start_tag, end_tag):
		pass
	
	def add_line_tags(self, start_tag, end_tag):
		document = self.view.get_buffer()
		selection = document.get_selection_bounds()
		if selection != ():
			(start, end) = selection
			if start.ends_line():
				start.forward_line()
			elif not start.starts_line():
				start.set_line_offset(0)
			if end.starts_line():
				end.backward_char()
			elif not end.ends_line():
				end.forward_to_line_end()
		else:
			start = document.get_iter_at_mark(document.get_insert())
			end = document.get_iter_at_mark(document.get_insert())
		new_code = self.add_tags_characters(document, start_tag, end_tag, start, end)
	
	def add_word_tags(self, start_tag, end_tag):
		document = self.view.get_buffer()
		selection = document.get_selection_bounds()
		if selection != ():
			(start, end) = selection
		else:
			return
		new_code = self.add_tags_characters(document, start_tag, end_tag, start, end)
	
	def format_title(self, level):
		level = level + 1
		self.add_line_tags('#'*level + ' ', ' ' + '#'*level)
		
	def format_bold(self):
		self.add_word_tags('**', '**')
		
	def list_unordered(self):
		self.add_line_tags('- ', '')
		
	def list_ordered(self):
		self.add_line_tags('1. ', '')
	
	def format_italic(self):
		self.add_word_tags('*', '*')
	
	def format_monospace(self):
		self.add_word_tags('`', '`')
	
	def format_quote(self):
		self.add_line_tags('> ', '')
		
	def format_underline(self):
		self.add_word_tags('__', '__')
	
	def insert_link(self, window):
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
		
	def add_tags_characters(self, document, start_tag, end_tag, start, end):
		smark = document.create_mark("start", start, False)
		imark = document.create_mark("iter", start, False)
		emark = document.create_mark("end", end, False)
		number_lines = end.get_line() - start.get_line() + 1
		document.begin_user_action()

		for i in range(0, number_lines):
			iter = document.get_iter_at_mark(imark)
			if not iter.ends_line():
				document.insert(iter, start_tag)
				if end_tag is not None:
					if i != number_lines -1:
						iter = document.get_iter_at_mark(imark)
						iter.forward_to_line_end()
						document.insert(iter, end_tag)
					else:
						iter = document.get_iter_at_mark(emark)
						document.insert(iter, end_tag)
			iter = document.get_iter_at_mark(imark)
			iter.forward_line()
			document.delete_mark(imark)
			imark = document.create_mark("iter", iter, True)

		document.end_user_action()

		document.delete_mark(imark)
		new_start = document.get_iter_at_mark(smark)
		new_end = document.get_iter_at_mark(emark)
		if not new_start.ends_line():
			self.backward_tag(new_start, start_tag)
		document.select_range(new_start, new_end)
		document.delete_mark(smark)
		document.delete_mark(emark)

	def forward_tag(self, iter, tag):
		iter.forward_chars(len(tag))

	def backward_tag(self, iter, tag):
		iter.backward_chars(len(tag))

##################################################
