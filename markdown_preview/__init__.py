import subprocess, gi, os, markdown
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, WebKit2, GLib

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

from .prefs import MdConfigWidget
from .preview import MdPreviewBar
from .window import MdPreviewWindow

try:
	import gettext
	gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
	gettext.textdomain('gedit-plugin-markdown-preview')
	_ = gettext.gettext
except:
	_ = lambda s: s

MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'
BASE_TEMP_NAME = '/tmp/gedit_plugin_markdown_preview'

####### ####### #######

class MarkdownGeditPluginApp(GObject.Object, Gedit.AppActivatable):
	__gtype_name__ = 'MarkdownGeditPluginApp'
	app = GObject.property(type=Gedit.App)

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		self.build_main_menu()

	def do_deactivate(self):
		self._remove_menu()

	def build_main_menu(self):
		self.menu_ext = self.extend_menu('tools-section')
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menus.ui'))
#		menu = builder.get_object('md-preview-menu')
#		self.menu_section = Gio.MenuItem.new_submenu(_("Markdown Preview"), menu)
#		self.menu_ext.append_menu_item(self.menu_section)

		# Show the zoom settings as a submenu here because it's ugly otherwise
		menu = builder.get_object('md-preview-actions')
		self.menu_section_actions = Gio.MenuItem.new_section(_("Markdown Preview"), menu)
		self.menu_ext.append_menu_item(self.menu_section_actions)
		menu = builder.get_object('md-preview-zoom')
		self.menu_section_zoom = Gio.MenuItem.new_submenu(_("Zoom"), menu)
		self.menu_ext.append_menu_item(self.menu_section_zoom)
		menu = builder.get_object('md-preview-settings')
		self.menu_section_settings = Gio.MenuItem.new_section(None, menu)
		self.menu_ext.append_menu_item(self.menu_section_settings)

	def _remove_menu(self):
		self.menu_ext = None # FIXME ?
		self.menu_item = None

####### ####### #######

class MarkdownGeditPluginWindow(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable):
	window = GObject.property(type=Gedit.Window)
	__gtype_name__ = 'MarkdownGeditPluginWindow'

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
		action_export = Gio.SimpleAction(name='md_prev_export_doc')
		action_print = Gio.SimpleAction(name='md_prev_print_doc')
		action_insert = Gio.SimpleAction(name='md_prev_insert_picture')
		action_export.connect('activate', self.export_doc)
		action_print.connect('activate', self.print_doc)
		action_insert.connect('activate', self.insert_picture)
		
		self.window.add_action(action_export)
		self.window.add_action(action_print)
		self.window.add_action(action_insert)

		action_zoom_in = Gio.SimpleAction(name='md_prev_zoom_in')
		action_zoom_original = Gio.SimpleAction(name='md_prev_zoom_original')
		action_zoom_out = Gio.SimpleAction(name='md_prev_zoom_out')
		action_zoom_in.connect('activate', self.preview.on_zoom_in)
		action_zoom_original.connect('activate', self.preview.on_zoom_original)
		action_zoom_out.connect('activate', self.preview.on_zoom_out)
		
		self.window.add_action(action_zoom_in)
		self.window.add_action(action_zoom_original)
		self.window.add_action(action_zoom_out)

		action_paginated = Gio.SimpleAction().new_stateful('md_prev_set_paginated', \
		None, GLib.Variant.new_boolean(False))
		action_paginated.connect('change-state', self.preview.on_set_paginated)
		
		action_next = Gio.SimpleAction(name='md_prev_next')
		action_next.connect('activate', self.preview.on_next_page)
		
		action_previous = Gio.SimpleAction(name='md_prev_previous')
		action_previous.connect('activate', self.preview.on_previous_page)

		action_autoreload = Gio.SimpleAction().new_stateful('md_prev_set_autoreload', \
		None, GLib.Variant.new_boolean(self.preview.auto_reload))
		action_autoreload.connect('change-state', self.preview.on_set_reload)
		
		self.action_reload_preview = Gio.SimpleAction(name='md_prev_reload')
		self.action_reload_preview.connect('activate', self.preview.on_reload)

		action_panel = Gio.SimpleAction().new_stateful('md_prev_panel', \
		GLib.VariantType.new('s'), GLib.Variant.new_string(self._settings.get_string('position')))
		action_panel.connect('change-state', self.preview.on_change_panel_from_popover)

		action_presentation = Gio.SimpleAction(name='md_prev_presentation')
		action_presentation.connect('activate', self.preview.on_presentation)

		action_hide = Gio.SimpleAction(name='md_prev_hide')
		action_hide.connect('activate', self.preview.on_hide_panel)
		
		self.window.add_action(action_paginated)
		self.window.add_action(action_next)
		self.window.add_action(action_previous)
		self.window.add_action(action_panel)
		self.window.add_action(action_presentation)
		self.window.add_action(action_hide)
		self.window.add_action(action_autoreload)
		self.window.add_action(self.action_reload_preview)
	
	def recognize_format(self):
		doc = self.window.get_active_document()
		# It will not load documents which are not .md/.html/.tex
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		self.preview.display_warning(False, '')
		if temp[len(temp)-1] == 'md':
			return 'md'
		elif temp[len(temp)-1] == 'html':
			self.window.lookup_action('md_prev_insert_picture').set_enabled(False)
			return 'html'
		elif temp[len(temp)-1] == 'tex':
			self.window.lookup_action('md_prev_insert_picture').set_enabled(False)
			return 'tex'
		# The current content is not replaced, which allows document consulation while working on a file
		self.window.lookup_action('md_prev_export_doc').set_enabled(False)
		self.window.lookup_action('md_prev_print_doc').set_enabled(False)
		self.window.lookup_action('md_prev_insert_picture').set_enabled(False)
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

	def on_reload(self, *args):
		# Guard clause: it will not load documents which are not .md
		if self.recognize_format() is 'error':
			if len(self.panel.get_children()) is 1: # FIXME 1 pour bottom mais 2 pour side
				self.panel.hide()
			return

		elif self.recognize_format() is 'html':
			self.panel.show()
			doc = self.window.get_active_document()
			start, end = doc.get_bounds()
			html_string = doc.get_text(start, end, True)
			pre_string = '<html><head><meta charset="utf-8" /></head><body>'
			post_string = '</body></html>'
			html_string = self.current_page(html_string)
			html_content = pre_string + html_string + post_string

		elif self.recognize_format() is 'tex':
			self.panel.show()
			doc = self.window.get_active_document()
			file_path = doc.get_location().get_path()

			# It uses pandoc to produce the html code
			pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
				self._settings.get_string('style') + '" /></head><body>'
			post_string = '</body></html>'
			result = subprocess.run(['pandoc', file_path], stdout=subprocess.PIPE)
			html_string = result.stdout.decode('utf-8')
			html_string = self.current_page(html_string)
			html_content = pre_string + html_string + post_string

		else:
			self.panel.show()
			# Get the current document, or the temporary document if requested
			doc = self.window.get_active_document()
			if self.auto_reload:
				start, end = doc.get_bounds()
				unsaved_text = doc.get_text(start, end, True)
				f = open(BASE_TEMP_NAME + '.md', 'w')
				f.write(unsaved_text)
				f.close()
				file_path = self.temp_file_md.get_path()
			else:
				file_path = doc.get_location().get_path()

			# It uses pandoc to produce the html code
			pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
				self._settings.get_string('style') + '" /></head><body>'
			post_string = '</body></html>'
			result = subprocess.run(['pandoc', file_path], stdout=subprocess.PIPE)
			html_string = result.stdout.decode('utf-8')
			html_string = self.current_page(html_string)
			html_content = pre_string + html_string + post_string

		# The html code is converted into bytes
		my_string = GLib.String()
		my_string.append(html_content)
		bytes_content = my_string.free_to_bytes()

		# This uri will be used as a reference for links and images using relative paths
		dummy_uri = self.get_dummy_uri()

		# The content is loaded
		self._webview.load_bytes(bytes_content, 'text/html', 'UTF-8', dummy_uri)

		self.window.lookup_action('md_prev_export_doc').set_enabled(True)
		self.window.lookup_action('md_prev_print_doc').set_enabled(True)
		self.window.lookup_action('md_prev_insert_picture').set_enabled(True)

	def current_page(self, html_string):
		# Guard clause
		if not self.is_paginated:
			return html_string

		html_pages = html_string.split('<hr />')
		self.page_number = len(html_pages)
		if self.page_index >= self.page_number:
			self.page_index = self.page_number-1
		html_current_page = html_pages[self.page_index]
		return html_current_page

	def get_dummy_uri(self):
		# Support for relative paths is cool, but breaks CSS in many cases
		if self._settings.get_boolean('relative'):
			return self.window.get_active_document().get_location().get_uri()
		else:
			return 'file://'

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

	def on_presentation(self, *args):
		self.preview_bar.remove(self._webview)
		w = MdPreviewWindow(self)
		w.window.present()

	def do_create_configure_widget(self):
		# Just return your box, PeasGtk will automatically pack it into a dialog and show it.
		widget = MdConfigWidget(self.plugin_info.get_data_dir())
		return widget
	
	def insert_picture(self, a, b):
		# Guard clause: it will not load dialog if the file is not .md
		if self.recognize_format() != 'md':
			return

		# Building a FileChooserDialog for pictures
		file_chooser = Gtk.FileChooserDialog(_("Select a picture"), self.window,
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
			doc = self.window.get_active_document()
			picture_path = '![](' + file_chooser.get_filename() + ')'
			iter = doc.get_iter_at_mark(doc.get_insert())
			doc.insert(iter, picture_path)
		file_chooser.destroy()

	def export_doc(self, a, b):
		
		dialog = Gtk.Dialog(use_header_bar=True)
		dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
		dialog.add_button(_("Next"), Gtk.ResponseType.OK)
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'export.ui'))
		dialog.get_content_area().add(builder.get_object('content-area'))
		response_id = dialog.run()
		if response_id == Gtk.ResponseType.CANCEL:
			dialog.destroy()
			return
		elif response_id == Gtk.ResponseType.OK:
			
			# TODO
			dialog.destroy()
		
		# TODO
	
		if (self.recognize_format() == 'tex') and self._settings.get_boolean('pdflatex'): #FIXME mauvais path?
			subprocess.run(['pdflatex', self.window.get_active_document().get_location().get_path()])
		else:
			file_chooser = Gtk.FileChooserDialog(_("Export the preview"), self.window,
				Gtk.FileChooserAction.SAVE,
				(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
				Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
			response = file_chooser.run()
			
			# It gets the chosen file's path
			if response == Gtk.ResponseType.OK:
				if (file_chooser.get_filename().split('.')[-1] == 'html'):
#					subprocess.run(['pandoc', self.window.get_active_document().get_location().get_path(), \
#						'-o', file_chooser.get_filename()])
					subprocess.run(['pandoc', self.window.get_active_document().get_location().get_path(), \
						'-t', 'revealjs', '-s',
						'-V', 'revealjs-url=http://lab.hakim.se/reveal-js',
						'-o', file_chooser.get_filename()])
						
					pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
						self._settings.get_string('style') + '" /></head><body>'
					post_string = '</body></html>'
					
					with open(file_chooser.get_filename(), 'r+') as f:
						content = f.read()
						f.seek(0, 0)
						f.write(pre_string.rstrip('\r\n') + '\n' + content)
						f.close()
						
					f=open(file_chooser.get_filename(),'a')
					f.write(post_string)
					f.close()
				else:
					subprocess.run(['pandoc', self.window.get_active_document().get_location().get_path(), \
						'-o', file_chooser.get_filename()])
			file_chooser.destroy()

	def print_doc(self, a, b):
		p = WebKit2.PrintOperation.new(self.preview._webview)
		p.run_dialog()

####### ####### #######

class MarkdownGeditPluginView(GObject.Object, Gedit.ViewActivatable):
	view = GObject.Property(type=Gedit.View)

	def __init__(self):
		self.popup_handler_id = 0
		GObject.Object.__init__(self)

	def do_activate(self):
		menu_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menus.ui'))
		self.md_prev_menu = Gtk.Menu().new_from_model(menu_builder.get_object('right-click-menu'))
		self.popup_handler_id = self.view.connect('populate-popup', self.populate_popup)

	def do_deactivate(self):
		if self.popup_handler_id != 0:
			self.view.disconnect(self.popup_handler_id)
			self.popup_handler_id = 0

	def populate_popup(self, view, popup):
		if not isinstance(popup, Gtk.MenuShell):
			return

		item = Gtk.SeparatorMenuItem()
		item.show()
		popup.append(item)
		
		item = Gtk.MenuItem(_("Markdown tags"))
		item.set_submenu(self.md_prev_menu)
		item.show()
#		if pas_du_md: # TODO
#			item.set_sensitive(False)
		popup.append(item)

##################################################
