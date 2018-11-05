import subprocess, gi, os, markdown
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, WebKit2, GLib

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

from .window import MdPreviewWindow

MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'
BASE_TEMP_NAME = '/tmp/gedit_plugin_markdown_preview'

class MdPreviewBar(Gtk.Box):
	__gtype_name__ = 'MdPreviewBar'
	
	def __init__(self, parent_plugin, **kwargs):
		super().__init__(**kwargs)
		self.auto_reload = False
		self._compteur_laid = 0
		self.parent_plugin = parent_plugin

	def do_activate(self):
		self._handlers = []
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self._handlers.append( self._settings.connect('changed::position', self.change_panel) )
		self.is_paginated = False
		self.connect_preview_menu()
		self.build_preview_ui()
		self._handlers.append( self.parent_plugin.window.connect('active-tab-changed', self.on_reload) )
		self.page_index = 0
		self.page_number = 1
		self.temp_file_md = Gio.File.new_for_path(BASE_TEMP_NAME + '.md')
		self.parent_plugin.window.lookup_action('md_prev_export_doc').set_enabled(False)
		self.parent_plugin.window.lookup_action('md_prev_print_doc').set_enabled(False)
		self.parent_plugin.window.lookup_action('md_prev_insert_picture').set_enabled(False)

	# This is called every time the gui is updated
	def do_update_state(self):
		if not self.panel.props.visible:
			return
		if self.parent_plugin.window.get_active_view() is not None:
			if self.auto_reload:
				if self._compteur_laid > 3:
					self._compteur_laid = 0
					self.on_reload()
				else:
					self._compteur_laid = self._compteur_laid + 1

	def do_deactivate(self):
		self._settings.disconnect(self._handlers[0])
		self.parent_plugin.window.disconnect(self._handlers[1])
		self.delete_temp_file()
		self.remove_from_panel()
		self.preview_bar.destroy()

	def connect_preview_menu(self):
		action_export = Gio.SimpleAction(name='md_prev_export_doc')
		action_print = Gio.SimpleAction(name='md_prev_print_doc')
		action_insert = Gio.SimpleAction(name='md_prev_insert_picture')
		action_export.connect('activate', self.export_doc)
		action_print.connect('activate', self.print_doc)
		action_insert.connect('activate', self.insert_picture)
		self.parent_plugin.window.add_action(action_export)
		self.parent_plugin.window.add_action(action_print)
		self.parent_plugin.window.add_action(action_insert)

		action_zoom_in = Gio.SimpleAction(name='md_prev_zoom_in')
		action_zoom_original = Gio.SimpleAction(name='md_prev_zoom_original')
		action_zoom_out = Gio.SimpleAction(name='md_prev_zoom_out')
		action_zoom_in.connect('activate', self.on_zoom_in)
		action_zoom_original.connect('activate', self.on_zoom_original)
		action_zoom_out.connect('activate', self.on_zoom_out)
		self.parent_plugin.window.add_action(action_zoom_in)
		self.parent_plugin.window.add_action(action_zoom_original)
		self.parent_plugin.window.add_action(action_zoom_out)

		action_paginated = Gio.SimpleAction().new_stateful('md_prev_set_paginated', \
		None, GLib.Variant.new_boolean(False))
		action_paginated.connect('change-state', self.on_set_paginated)
		self.parent_plugin.window.add_action(action_paginated)

		action_autoreload = Gio.SimpleAction().new_stateful('md_prev_set_autoreload', \
		None, GLib.Variant.new_boolean(self.auto_reload))
		action_autoreload.connect('change-state', self.on_set_reload)
		self.parent_plugin.window.add_action(action_autoreload)

		action_panel = Gio.SimpleAction().new_stateful('md_prev_panel', \
		GLib.VariantType.new('s'), GLib.Variant.new_string(self._settings.get_string('position')))
		action_panel.connect('change-state', self.on_change_panel_from_popover)
		self.parent_plugin.window.add_action(action_panel)

		action_presentation = Gio.SimpleAction(name='md_prev_presentation')
		action_presentation.connect('activate', self.on_presentation)
		self.parent_plugin.window.add_action(action_presentation)

		action_hide = Gio.SimpleAction(name='md_prev_hide')
		action_hide.connect('activate', self.on_hide_panel)
		self.parent_plugin.window.add_action(action_hide)

		self.action_reload_preview = Gio.SimpleAction(name='md_prev_reload')
		self.action_reload_preview.connect('activate', self.on_reload)
		self.parent_plugin.window.add_action(self.action_reload_preview)

	def build_preview_ui(self):
		ui_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'preview.ui'))
		self.preview_bar = ui_builder.get_object('preview_bar')
		
		# This is the preview itself
		self._webview = WebKit2.WebView()
		self._webview.connect('context-menu', self.on_context_menu)
		self.preview_bar.pack_start(self._webview, expand=True, fill=True, padding=0)

		# Building UI elements
		menuBtn = ui_builder.get_object('menu_btn')
		menu_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menu.ui'))
		self.menu_popover = Gtk.Popover().new_from_model(menuBtn, menu_builder.get_object('md-preview-menu'))
		menuBtn.set_popover(self.menu_popover)
		
		self.build_search_popover()
		searchBtn = ui_builder.get_object('search_btn')
		self._search_popover.set_relative_to(searchBtn)
		searchBtn.set_popover(self._search_popover)

		self.buttons_main_box = ui_builder.get_object('buttons_main_box')
		self.pages_box = ui_builder.get_object('pages_box')
		self.warning_icon = ui_builder.get_object('warning_icon')
		refreshBtn = ui_builder.get_object('refresh_btn')
		previousBtn = ui_builder.get_object('previous_btn')
		nextBtn = ui_builder.get_object('next_btn')
		refreshBtn.connect('clicked', self.on_reload)
		previousBtn.connect('clicked', self.on_previous_page)
		nextBtn.connect('clicked', self.on_next_page)

		self.show_on_panel()

	def on_context_menu(self, a, b, c, d):
		if d.context_is_link():
			# It's not possible to...
			b.remove(b.get_item_at_position(2)) # download its target
			b.remove(b.get_item_at_position(1)) # open a link in a new window
			# TODO: open with gedit, open in defaut browser?
		elif d.context_is_image():
			# It's not possible to...
#			b.remove(b.get_item_at_position(1)) # "save [it] as"
			b.remove(b.get_item_at_position(0)) # open an image in a new window
		elif d.context_is_selection():
			pass
		else:
			b.remove_all()
		reloadItem = WebKit2.ContextMenuItem.new_from_gaction(self.action_reload_preview, _("Reload the preview"), None)
		b.append(reloadItem)
		return False

	def build_search_popover(self):
		some_damn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self._search_popover = Gtk.Popover()
		search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, visible=True)

		upBtn = Gtk.Button().new_from_icon_name('go-up-symbolic', Gtk.IconSize.BUTTON)
		upBtn.connect('clicked', self.on_search_up)
		downBtn = Gtk.Button().new_from_icon_name('go-down-symbolic', Gtk.IconSize.BUTTON)
		downBtn.connect('clicked', self.on_search_down)

		self._search_entry = Gtk.SearchEntry()
		self._search_entry.connect('search-changed', self.on_search_changed)
		search_box.add(self._search_entry)
		search_box.add(upBtn)
		search_box.add(downBtn)
		search_box.get_style_context().add_class('linked')

		self.find_controller = self._webview.get_find_controller()
		self.find_controller.connect('counted-matches', self.on_count_change)
		self.count_label = Gtk.Label(_("No result"))

		some_damn_box.add(search_box)
		some_damn_box.add(self.count_label)
		some_damn_box.show_all()
		self._search_popover.add(some_damn_box)

	def on_change_panel_from_popover(self, *args):
		if GLib.Variant.new_string('side') == args[1]:
			self._settings.set_string('position', 'side')
			args[0].set_state(GLib.Variant.new_string('side'))
		else:
			self._settings.set_string('position', 'bottom')
			args[0].set_state(GLib.Variant.new_string('bottom'))

	def on_set_reload(self, *args):
		if not args[0].get_state():
			self.auto_reload = True
			self.on_reload()
			args[0].set_state(GLib.Variant.new_boolean(True))
		else:
			self.auto_reload = False
			args[0].set_state(GLib.Variant.new_boolean(False))

	def on_hide_panel(self, *args):
		if self._settings.get_string('position') == 'bottom':
			self.parent_plugin.window.get_bottom_panel().set_property('visible', False)
		else:
			self.parent_plugin.window.get_side_panel().set_property('visible', False)

	def on_set_paginated(self, *args):
		if not args[0].get_state():
			self.is_paginated = True
			self.parent_plugin.window.lookup_action('md_prev_next').set_enabled(True)
			self.parent_plugin.window.lookup_action('md_prev_previous').set_enabled(True)
			self.pages_box.props.visible = True
			self.on_reload()
			args[0].set_state(GLib.Variant.new_boolean(True))
		else:
			self.is_paginated = False
			self.parent_plugin.window.lookup_action('md_prev_next').set_enabled(False)
			self.parent_plugin.window.lookup_action('md_prev_previous').set_enabled(False)
			self.pages_box.props.visible = False
			self.on_reload()
			args[0].set_state(GLib.Variant.new_boolean(False))

	def on_previous_page(self, *args):
		if self.page_index > 0:
			self.page_index = self.page_index -1
			self.on_reload()

	def on_next_page(self, *args):
		self.page_index = self.page_index +1
		self.on_reload()

	def delete_temp_file(self):
		if self.temp_file_md.query_exists():
			self.temp_file_md.delete()

	def recognize_format(self):
		doc = self.parent_plugin.window.get_active_document()
		# It will not load documents which are not .md/.html/.tex
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		self.display_warning(False, '')
		if temp[len(temp)-1] == 'md':
			return 'md'
		elif temp[len(temp)-1] == 'html':
			self.parent_plugin.window.lookup_action('md_prev_insert_picture').set_enabled(False)
			return 'html'
		elif temp[len(temp)-1] == 'tex':
			self.parent_plugin.window.lookup_action('md_prev_insert_picture').set_enabled(False)
			return 'tex'
		# The current content is not replaced, which allows document consulation while working on a file
		self.parent_plugin.window.lookup_action('md_prev_export_doc').set_enabled(False)
		self.parent_plugin.window.lookup_action('md_prev_print_doc').set_enabled(False)
		self.parent_plugin.window.lookup_action('md_prev_insert_picture').set_enabled(False)
		if doc.is_untitled():
			self.display_warning(True, _("Can't preview an unsaved document"))
		else:
			self.display_warning(True, _("Unsupported type of document: ") + name)
		return 'error'

	def display_warning(self, visible, text):
		self.warning_icon.set_tooltip_text(text)
		self.warning_icon.props.visible = visible

	def on_reload(self, *args):
		# Guard clause: it will not load documents which are not .md
		if self.recognize_format() is 'error':
			if len(self.panel.get_children()) is 1: # FIXME 1 pour bottom mais 2 pour side
				self.panel.hide()
			return

		elif self.recognize_format() is 'html':
			self.panel.show()
			doc = self.parent_plugin.window.get_active_document()
			start, end = doc.get_bounds()
			html_string = doc.get_text(start, end, True)
			pre_string = '<html><head><meta charset="utf-8" /></head><body>'
			post_string = '</body></html>'
			html_string = self.current_page(html_string)
			html_content = pre_string + html_string + post_string

		elif self.recognize_format() is 'tex':
			self.panel.show()
			doc = self.parent_plugin.window.get_active_document()
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
			doc = self.parent_plugin.window.get_active_document()
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

		self.parent_plugin.window.lookup_action('md_prev_export_doc').set_enabled(True)
		self.parent_plugin.window.lookup_action('md_prev_print_doc').set_enabled(True)
		self.parent_plugin.window.lookup_action('md_prev_insert_picture').set_enabled(True)

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
			return self.parent_plugin.window.get_active_document().get_location().get_uri()
		else:
			return 'file://'

	def show_on_panel(self):
		# Get the bottom bar (A Gtk.Stack), or the side bar, and add our bar to it.
		if self._settings.get_string('position') == 'bottom':
			self.panel = self.parent_plugin.window.get_bottom_panel()
			self.preview_bar.props.orientation = Gtk.Orientation.HORIZONTAL
			self.buttons_main_box.props.orientation = Gtk.Orientation.VERTICAL
		else:
			self.panel = self.parent_plugin.window.get_side_panel()
			self.preview_bar.props.orientation = Gtk.Orientation.VERTICAL
			self.buttons_main_box.props.orientation = Gtk.Orientation.HORIZONTAL
		self.panel.add_titled(self.preview_bar, 'markdown_preview', _("Markdown Preview"))
		self.panel.set_visible_child(self.preview_bar)
		self.preview_bar.show_all()
		self.pages_box.props.visible = self.is_paginated
		if self.parent_plugin.window.get_state() is 'STATE_NORMAL':
			self.on_reload()

	def remove_from_panel(self):
		if self.panel is not None:
			self.panel.remove(self.preview_bar)

	def on_zoom_in(self, *args):
		if self._webview.get_zoom_level() < 10:
			self._webview.set_zoom_level(self._webview.get_zoom_level() + 0.1)
		return self._webview.get_zoom_level()

	def on_zoom_out(self, *args):
		if self._webview.get_zoom_level() > 0.15:
			self._webview.set_zoom_level(self._webview.get_zoom_level() - 0.1)
		return self._webview.get_zoom_level()

	def on_zoom_original(self, *args):
		self._webview.set_zoom_level(1)

	########

	def on_search_changed(self, a):
		text = self._search_entry.get_text()
		self.find_controller.count_matches(text, WebKit2.FindOptions.CASE_INSENSITIVE, 100)
		self.find_controller.search(text, WebKit2.FindOptions.CASE_INSENSITIVE, 100)

	def on_search_up(self, btn):
		self.find_controller.search_previous()

	def on_search_down(self, btn):
		self.find_controller.search_next()

	def on_count_change(self, find_ctrl, number):
		self.count_label.set_text(_("%s results") % number)

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

	# XXX rien à foutre là
	def insert_picture(self, a, b):
		# Guard clause: it will not load dialog if the file is not .md
		if self.recognize_format() != 'md':
			return

		# Building a FileChooserDialog for pictures
		file_chooser = Gtk.FileChooserDialog(_("Select a picture"), self.parent_plugin.window,
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
			doc = self.parent_plugin.window.get_active_document()
			picture_path = '![](' + file_chooser.get_filename() + ')'
			iter = doc.get_iter_at_mark(doc.get_insert())
			doc.insert(iter, picture_path)
		file_chooser.destroy()

	def export_doc(self, a, b):
		
		
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'export.ui'))
		dialog = builder.get_object('export_dialog')
		dialog.run()
	
	
		if (self.recognize_format() == 'tex') and self._settings.get_boolean('pdflatex'): #FIXME mauvais path?
			subprocess.run(['pdflatex', self.parent_plugin.window.get_active_document().get_location().get_path()])
		else:
			file_chooser = Gtk.FileChooserDialog(_("Export the preview"), self.parent_plugin.window,
				Gtk.FileChooserAction.SAVE,
				(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
				Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
			response = file_chooser.run()
			
			# It gets the chosen file's path
			if response == Gtk.ResponseType.OK:
				if (file_chooser.get_filename().split('.')[-1] == 'html'):
#					subprocess.run(['pandoc', self.parent_plugin.window.get_active_document().get_location().get_path(), \
#						'-o', file_chooser.get_filename()])
					subprocess.run(['pandoc', self.parent_plugin.window.get_active_document().get_location().get_path(), \
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
					subprocess.run(['pandoc', self.parent_plugin.window.get_active_document().get_location().get_path(), \
						'-o', file_chooser.get_filename()])
			file_chooser.destroy()

	def print_doc(self, a, b):
		p = WebKit2.PrintOperation.new(self._webview)
		p.run_dialog()

##################################################
