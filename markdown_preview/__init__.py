import subprocess
import gi
import os
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, WebKit2, GLib

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	import gettext
	gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
	_ = lambda s: gettext.dgettext('gedit-plugin-markdown-preview', s)
except:
	_ = lambda s: s
	
#################
	
MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'
BASE_TEMP_NAME = '/tmp/gedit_plugin_markdown_preview'

class MarkdownGeditPluginApp(GObject.Object, Gedit.AppActivatable):
	__gtype_name__ = 'MarkdownGeditPluginApp'
	app = GObject.property(type=Gedit.App)
	
	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		self._build_menu()

	def do_deactivate(self):
		self._remove_menu()
	
	def _build_menu(self):
		self.menu_ext = self.extend_menu('file-section-1')
		menu = Gio.Menu()
		menu_item_export = Gio.MenuItem.new(_("Export the preview"), 'win.export_doc')
		menu_item_print = Gio.MenuItem.new(_("Print the preview"), 'win.print_doc')
		menu_item_insert = Gio.MenuItem.new(_("Insert a picture"), 'win.insert_picture')
#		menu_item_reload = Gio.MenuItem.new(_("Reload"), 'win.reload')
		menu.append_item(menu_item_export)
		menu.append_item(menu_item_print)
		menu.append_item(menu_item_insert)
#		menu.append_item(menu_item_reload)
		self.menu_section = Gio.MenuItem.new_section(_("Markdown Preview"), menu)
		self.menu_ext.append_menu_item(self.menu_section)
	
	def _remove_menu(self):
		self.menu_ext = None
		self.menu_item = None

class MarkdownGeditPluginWindow(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable):
	window = GObject.property(type=Gedit.Window)
	__gtype_name__ = 'MarkdownGeditPluginWindow'

	def __init__(self):
		GObject.Object.__init__(self)
		self.preview_bar = Gtk.Box()
		
		self._auto_reload = False
		self._compteur_laid = 0
	
	# This is called every time the gui is updated
	def do_update_state(self):
		if self.window.get_active_view() is not None:
			if self._auto_reload:
				if self._compteur_laid > 3:
					self._compteur_laid = 0
					self.on_reload(None, None)
				else:
					self._compteur_laid = self._compteur_laid + 1
	
	def do_activate(self):
		# Defining the action which was set earlier in AppActivatable.
		self._handlers = []
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self._isAtBottom = (self._settings.get_string('position') == 'bottom')
		self._handlers.append( self._settings.connect('changed::position', self.change_panel) )
		self._is_paginated = False
		self.insert_in_adequate_panel()
		self._handlers.append( self.window.connect('active-tab-changed', self.on_reload) )
		self._page_index = 0
		self.temp_file_md = Gio.File.new_for_path(BASE_TEMP_NAME + '.md')
		self._connect_menu()
		self.window.lookup_action('export_doc').set_enabled(False)
		self.window.lookup_action('print_doc').set_enabled(False)
		self.window.lookup_action('insert_picture').set_enabled(False)
				
	def do_deactivate(self):
		self._settings.disconnect(self._handlers[0])
		self.window.disconnect(self._handlers[1])		
		self.delete_temp_file()
		self._remove_from_panel()

	def _connect_menu(self):
		action_export = Gio.SimpleAction(name='export_doc')
		action_print = Gio.SimpleAction(name='print_doc')
		action_insert = Gio.SimpleAction(name='insert_picture')
		action_export.connect('activate', self.export_doc)
		action_print.connect('activate', self.print_doc)
		action_insert.connect('activate', self.insert_picture)
		self.window.add_action(action_export)
		self.window.add_action(action_print)
		self.window.add_action(action_insert)
		
#		action_reload = Gio.SimpleAction(name='reload')
#		action_reload.connect('activate', self.on_reload)
#		self.window.add_action(action_reload)
		
	def insert_in_adequate_panel(self):
		# This is the preview itself
		self._webview = WebKit2.WebView()
		self._webview.connect('context-menu', self.on_context_menu)
		
		searchBtn = self.build_search_popover()
		menuBtn = self.build_menu_popover()
		
		# Building the interface
		self.pages_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		
		main_box = Gtk.Box(margin_left=5, margin_right=5, margin_top=5, margin_bottom=5, spacing=2)
		main_box.props.homogeneous = False
		self.pages_box.get_style_context().add_class('linked')

		if self._isAtBottom:
			self.preview_bar.props.orientation = Gtk.Orientation.HORIZONTAL
			main_box.props.orientation = Gtk.Orientation.VERTICAL
		else:
			self.preview_bar.props.orientation = Gtk.Orientation.VERTICAL
			main_box.props.orientation = Gtk.Orientation.HORIZONTAL
		
		refreshBtn = self.build_button('toggled', 'view-refresh-symbolic')
		refreshBtn.set_active(self._auto_reload)
		refreshBtn.connect('toggled', self.on_set_reload)

		previousBtn = self.build_button('clicked', 'go-previous-symbolic')
		previousBtn.connect('clicked', self.on_previous_page)
		self.pages_box.add(previousBtn)
		
		nextBtn = self.build_button('clicked', 'go-next-symbolic')
		nextBtn.connect('clicked', self.on_next_page)
		self.pages_box.add(nextBtn)
		
		main_box.pack_end(menuBtn, expand=False, fill=False, padding=0)
		main_box.pack_end(searchBtn, expand=False, fill=False, padding=0)
		main_box.pack_start(refreshBtn, expand=False, fill=False, padding=0)
		main_box.pack_start(self.pages_box, expand=False, fill=False, padding=0)

		# main_box only contains the buttons, it will pack at the end (bottom or right) of
		# the preview_bar object, where the webview has already been added.
		self.preview_bar.pack_end(main_box, expand=False, fill=False, padding=0)
		self.preview_bar.pack_start(self._webview, expand=True, fill=True, padding=0)
		
		self.show_on_panel()

	def build_menu_popover(self):
		
		self.position_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		self.zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		
		self.zoom_box.get_style_context().add_class('linked')
		self.position_box.get_style_context().add_class('linked')
		
		menuBtn = self.build_button('toggled', 'open-menu-symbolic')
		menuBtn.connect('toggled', self.on_toggle_menu_mode)
		
		self._menu_popover = Gtk.Popover()
		self._menu_popover.set_relative_to(menuBtn)
		
		menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		
		self._menu_popover.add(menu_box)
		self._menu_popover.connect('closed', self.on_popover_menu_closed, menuBtn)

		############
		
		zoomInBtn = self.build_button('clicked', 'zoom-in-symbolic')
		zoomInBtn.connect('clicked', self.on_zoom_in)
		self.zoom_box.pack_end(zoomInBtn, expand=True, fill=True, padding=0)
		
		zoomOriginalBtn = self.build_button('clicked', 'zoom-original-symbolic')
		zoomOriginalBtn.connect('clicked', self.on_zoom_original)
		self.zoom_box.pack_end(zoomOriginalBtn, expand=True, fill=True, padding=0)
		
		zoomOutBtn = self.build_button('clicked', 'zoom-out-symbolic')
		zoomOutBtn.connect('clicked', self.on_zoom_out)
		self.zoom_box.pack_end(zoomOutBtn, expand=True, fill=True, padding=0)

		############
		
		paginatedBtn = Gtk.ToggleButton(_("Display only one page"))
		paginatedBtn.connect('toggled', self.on_set_paginated)
		paginatedBtn.set_relief(Gtk.ReliefStyle.NONE)

		hideBtn = Gtk.Button(_("Hide the panel"))
		hideBtn.connect('clicked', self.on_hide_panel)
		hideBtn.set_relief(Gtk.ReliefStyle.NONE)

		insertBtn = Gtk.Button(_("Insert a picture"))
		insertBtn.connect('clicked', self.insert_picture, None)
		insertBtn.set_relief(Gtk.ReliefStyle.NONE)

		############
		
		self.sideBtn = self.build_button('toggled', 'go-first-symbolic')
		self.sideBtn.set_active(not self._isAtBottom)
		self.sideBtn.connect('toggled', self.change_position_for, 'side')
		self.position_box.pack_start(self.sideBtn, expand=True, fill=True, padding=0)
		
		self.bottomBtn = self.build_button('toggled', 'go-bottom-symbolic')
		self.bottomBtn.set_active(self._isAtBottom)
		self.bottomBtn.connect('toggled', self.change_position_for, 'bottom')
		self.position_box.pack_start(self.bottomBtn, expand=True, fill=True, padding=0)

		############
		
		menu_box.add(self.position_box)
		menu_box.add(hideBtn)
		menu_box.add(self.zoom_box)
		menu_box.add(paginatedBtn)
		menu_box.add(insertBtn)
		
		return menuBtn
	
	def on_context_menu(self, a, b, c, d):
		if d.context_is_link():
			# It's not possible to open a link in a new window or to download its target
			b.remove(b.get_item_at_position(1))
			b.remove(b.get_item_at_position(1))
			# TODO: open with gedit, open in defaut browser
		elif d.context_is_image():
			# It's not possible to open an image in a new window or to "save [it] as"
			b.remove(b.get_item_at_position(0))
			b.remove(b.get_item_at_position(0))
		elif d.context_is_selection():
			pass
		else:
			b.remove_all()
		action_reload_preview = Gio.SimpleAction(name='reload_preview')
		reloadItem = WebKit2.ContextMenuItem.new_from_gaction(action_reload_preview, _("Reload preview"), None)
		self.window.add_action(action_reload_preview)
		action_reload_preview.connect('activate', self.on_reload)
		b.append(reloadItem)
		return False
		
	def build_search_popover(self):
		
		some_damn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		
		searchBtn = self.build_button('toggled', 'system-search-symbolic')
		searchBtn.connect('toggled', self.on_toggle_search_mode)

		self._search_popover = Gtk.Popover()
		self._search_popover.set_relative_to(searchBtn)
		
		search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		
		upBtn = self.build_button('clicked', 'go-up-symbolic')
		upBtn.connect('clicked', self.on_search_up)
		downBtn = self.build_button('clicked', 'go-down-symbolic')
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
		self._search_popover.add(some_damn_box)
		self._search_popover.connect('closed', self.on_popover_search_closed, searchBtn)
		
		return searchBtn
		
	def build_button(self, mode, icon):
		if mode is 'toggled':
			btn = Gtk.ToggleButton()
		else:
			btn = Gtk.Button()
		image = Gtk.Image()
		image.set_from_icon_name(icon, Gtk.IconSize.BUTTON)
		btn.add(image)
		return btn
	
	def on_set_reload(self, btn):
		if btn.get_active():
			self._auto_reload = True
			self.on_reload(None, None)
		else:
			self._auto_reload = False

	def on_hide_panel(self, btn):
		if self._isAtBottom:
			self.window.get_bottom_panel().set_property('visible', False)
		else:
			self.window.get_side_panel().set_property('visible', False)

	def on_set_paginated(self, btn):
		if btn.get_active():
			self._is_paginated = True
			self.pages_box.props.visible = True
			self.on_reload(None, None)
		else:
			self._is_paginated = False
			self.pages_box.props.visible = False
			self.on_reload(None, None)
	
	def on_previous_page(self, btn):
		if self._page_index > 0:
			self._page_index = self._page_index -1
			self.on_reload(None, None)
#		else:
#			btn.set_sensitive(False)
			
	def on_next_page(self, btn):
		self._page_index = self._page_index +1
		self.on_reload(None, None)
	
	def delete_temp_file(self):
		if self.temp_file_md.query_exists():
			self.temp_file_md.delete()
	
	def recognize_format(self):
		doc = self.window.get_active_document()
		
		# It will not load documents which are not .md
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		if temp[len(temp)-1] == 'md':
			return 'md'
		elif temp[len(temp)-1] == 'html':
			self.window.lookup_action('insert_picture').set_enabled(False)
			return 'html'
		elif temp[len(temp)-1] == 'tex':
			self.window.lookup_action('insert_picture').set_enabled(False)
			return 'tex'
		else:
			# The current content is not replaced, which allows document consulation while working on a file
			self.window.lookup_action('export_doc').set_enabled(False)
			self.window.lookup_action('print_doc').set_enabled(False)
			self.window.lookup_action('insert_picture').set_enabled(False)
			return 'error'
	
	# This needs dummy parameters because it's connected to a signal which give arguments.
	def on_reload(self, osef, oseb):
		# Guard clause: it will not load documents which are not .md
		if self.recognize_format() is 'error':
			if len(self.panel.get_children()) is 1:
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
			if self._auto_reload:
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
		
		self.window.lookup_action('export_doc').set_enabled(True)
		self.window.lookup_action('print_doc').set_enabled(True)
		self.window.lookup_action('insert_picture').set_enabled(True)
	
	def current_page(self, html_string):
		# Guard clause
		if not self._is_paginated:
			return html_string
		
		html_pages = html_string.split('<hr />')
		if self._page_index is len(html_pages):
			self._page_index = self._page_index -1
		html_current_page = html_pages[self._page_index]
		return html_current_page
	
	def get_dummy_uri(self):
		# Support for relative paths is cool, but breaks CSS in many cases
		if self._settings.get_boolean('relative'):
			return self.window.get_active_document().get_location().get_uri()
		else:
			return 'file://'
	
	def show_on_panel(self):
		# Get the bottom bar (A Gtk.Stack), or the side bar, and add our bar to it.
		if self._isAtBottom:
			self.panel = self.window.get_bottom_panel()
		else:
			self.panel = self.window.get_side_panel()
		self.panel.add_titled(self.preview_bar, 'markdown_preview', _("Markdown Preview"))
		self.preview_bar.show_all()
		self.panel.set_visible_child(self.preview_bar)
		self.pages_box.props.visible = self._is_paginated
		self._search_entry.props.visible = False
		if self.window.get_state() is 'STATE_NORMAL':
			self.on_reload(None, None)

	def _remove_from_panel(self):
		self.panel.remove(self.preview_bar)
	
	def on_zoom_in(self, a):
		if self._webview.get_zoom_level() < 10:
			self._webview.set_zoom_level(self._webview.get_zoom_level() + 0.1)
		
	def on_zoom_out(self, a):
		if self._webview.get_zoom_level() > 0.15:
			self._webview.set_zoom_level(self._webview.get_zoom_level() - 0.1)
			
	def on_zoom_original(self, a):
		self._webview.set_zoom_level(1)
	
	def change_position_for(self, w, string):
		self._settings.set_string('position', string)
	
	########
	
	def on_search_changed(self, a):
		text = self._search_entry.get_text()
		self.find_controller.count_matches(text, WebKit2.FindOptions.CASE_INSENSITIVE, 100)
		self.find_controller.search(text, WebKit2.FindOptions.CASE_INSENSITIVE, 100)
	
	def on_toggle_search_mode(self, a):
		self._search_popover.show_all()
		
	def on_toggle_menu_mode(self, a):
		self._menu_popover.show_all()
	
	def on_popover_search_closed(self, popover, button):
		button.set_active(False)
	
	def on_popover_menu_closed(self, popover, button):
		button.set_active(False)
	
	def on_search_up(self, btn):
		self.find_controller.search_previous()
		
	def on_search_down(self, btn):
		self.find_controller.search_next()
	
	def on_count_change(self, find_ctrl, number):
		self.count_label.set_text(_("%s results") % number)
		
	########
	
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
	
	def change_panel(self, a, b):
		self._remove_from_panel()
		self.preview_bar = Gtk.Box()
		self._isAtBottom = (self._settings.get_string('position') == 'bottom')
		self.insert_in_adequate_panel()
		self.do_update_state()
		self.on_reload(None, None)
	
	def do_create_configure_widget(self):
		# Just return your box, PeasGtk will automatically pack it into a box and show it.
		widget = MdConfigWidget(self.plugin_info.get_data_dir())
		return widget.get_box()

	def export_doc(self, a, b):
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
					subprocess.run(['pandoc', self.window.get_active_document().get_location().get_path(), '-o', file_chooser.get_filename()])
				else: # in the future it shall behave differently
					subprocess.run(['pandoc', self.window.get_active_document().get_location().get_path(), '-o', file_chooser.get_filename()])
			file_chooser.destroy()
		
	def print_doc(self, a, b):
		p = WebKit2.PrintOperation.new(self._webview)
		p.run_dialog()

############################

class MdConfigWidget:

	def __init__(self, datadir):
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		
		self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=20, \
			margin_left=20,margin_right=20,margin_top=20,margin_bottom=20,homogeneous=True)
		#--------
		positionSettingBox=Gtk.Box()
		positionSettingBox.props.spacing = 20
		positionSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		positionSettingBox.pack_start(Gtk.Label(_("Preview position")), expand=False, fill=False, padding=0)
		positionCombobox = Gtk.ComboBoxText()
		positionCombobox.append('side', _("Side panel"))
		positionCombobox.append('bottom', _("Bottom panel"))
		positionCombobox.set_active_id(self._settings.get_string('position'))
		positionCombobox.connect('changed', self.on_position_changed)
		positionSettingBox.pack_end(positionCombobox, expand=False, fill=False, padding=0)
		#--------
		relativePathsSettingBox=Gtk.Box()
		relativePathsSettingBox.props.spacing = 20
		relativePathsSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		relativePathsSettingBox.pack_start(Gtk.Label(_("Use relative paths")), expand=False, fill=False, padding=0)
		relativePathsSwitch = Gtk.Switch()
		relativePathsSwitch.set_state(self._settings.get_boolean('relative'))
		relativePathsSwitch.connect('notify::active', self.on_relative_changed)
		relativePathsSettingBox.pack_end(relativePathsSwitch, expand=False, fill=False, padding=0)
		#--------
		pdflatexSettingBox=Gtk.Box()
		pdflatexSettingBox.props.spacing = 20
		pdflatexSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		pdflatexSettingBox.pack_start(Gtk.Label(_("Export .tex files with pdflatex")), expand=False, fill=False, padding=0)
		pdflatexSwitch = Gtk.Switch()
		pdflatexSwitch.set_state(self._settings.get_boolean('pdflatex'))
		pdflatexSwitch.connect('notify::active', self.on_pdflatex_changed)
		pdflatexSettingBox.pack_end(pdflatexSwitch, expand=False, fill=False, padding=0)
		#--------
		styleSettingBox=Gtk.Box()
		styleSettingBox.props.spacing = 20
		styleSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		styleSettingBox.pack_start(Gtk.Label(_("Stylesheet")), expand=False, fill=False, padding=0)
		self.styleLabel = Gtk.Label(self._settings.get_string('style'))
		styleButton = Gtk.Button()
		styleButton.connect('clicked', self.on_choose_css)
		styleImage = Gtk.Image()
		styleImage.set_from_icon_name('document-open-symbolic', Gtk.IconSize.BUTTON)
		styleButton.add(styleImage)
		styleSettingBox.pack_end(styleButton, expand=False, fill=False, padding=0)
		styleSettingBox.pack_end(self.styleLabel, expand=False, fill=False, padding=0)
		#--------
		self.box.add(positionSettingBox)
		self.box.add(relativePathsSettingBox)
		self.box.add(pdflatexSettingBox)
		self.box.add(styleSettingBox)
	
	def get_box(self):
		return self.box
		
	def on_position_changed(self, w):
		self._settings.set_string('position', w.get_active_id())
		
	def on_choose_css(self, w):
		# Building a FileChooserDialog for CSS
		file_chooser = Gtk.FileChooserDialog(_("Select a CSS file"), None, # FIXME
			Gtk.FileChooserAction.OPEN,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		onlyCSS = Gtk.FileFilter()
		onlyCSS.set_name(_("Stylesheet"))
		onlyCSS.add_mime_type('text/css')
		file_chooser.set_filter(onlyCSS)
		response = file_chooser.run()
		
		# It gets the chosen file's path
		if response == Gtk.ResponseType.OK:
			self.styleLabel.label = file_chooser.get_filename()
			self._settings.set_string('style', file_chooser.get_filename())
		file_chooser.destroy()
		
	def on_relative_changed(self, w, a):
		if w.get_state():
			self._settings.set_boolean('relative', True)
		else:
			self._settings.set_boolean('relative', False)
		
	def on_pdflatex_changed(self, w, a):
		if w.get_state():
			self._settings.set_boolean('pdflatex', True)
		else:
			self._settings.set_boolean('pdflatex', False)
	
