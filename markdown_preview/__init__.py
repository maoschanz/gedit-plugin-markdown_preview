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
		self.build_main_menu()

	def do_deactivate(self):
		self._remove_menu()
	
	def build_main_menu(self):
		self.menu_ext = self.extend_menu('tools-section')
		menu = Gio.Menu()
		menu_item_export = Gio.MenuItem.new(_("Export the preview"), 'win.md_prev_export_doc')
		menu_item_print = Gio.MenuItem.new(_("Print the preview"), 'win.md_prev_print_doc')
		menu_item_insert = Gio.MenuItem.new(_("Insert a picture"), 'win.md_prev_insert_picture')
		menu.append_item(menu_item_export)
		menu.append_item(menu_item_print)
		menu.append_item(menu_item_insert)
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
		self.auto_reload = False
		self._compteur_laid = 0
	
	def do_activate(self):
		# Defining the action which was set earlier in AppActivatable.
		self._handlers = []
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self._handlers.append( self._settings.connect('changed::position', self.change_panel) )
		self.is_paginated = False
		self.connect_preview_menu()
		self.build_preview_ui()
		self._handlers.append( self.window.connect('active-tab-changed', self.on_reload) )
		self.page_index = 0
		self.temp_file_md = Gio.File.new_for_path(BASE_TEMP_NAME + '.md')
		self.window.lookup_action('md_prev_export_doc').set_enabled(False)
		self.window.lookup_action('md_prev_print_doc').set_enabled(False)
		self.window.lookup_action('md_prev_insert_picture').set_enabled(False)
	
	# This is called every time the gui is updated
	def do_update_state(self):
		if not self.panel.props.visible:
			return
		if self.window.get_active_view() is not None:
			if self.auto_reload:
				if self._compteur_laid > 3:
					self._compteur_laid = 0
					self.on_reload()
				else:
					self._compteur_laid = self._compteur_laid + 1
				
	def do_deactivate(self):
		self._settings.disconnect(self._handlers[0])
		self.window.disconnect(self._handlers[1])		
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
		self.window.add_action(action_export)
		self.window.add_action(action_print)
		self.window.add_action(action_insert)
		
		action_zoom_in = Gio.SimpleAction(name='md_prev_zoom_in')
		action_zoom_original = Gio.SimpleAction(name='md_prev_zoom_original')
		action_zoom_out = Gio.SimpleAction(name='md_prev_zoom_out')
		action_zoom_in.connect('activate', self.on_zoom_in)
		action_zoom_original.connect('activate', self.on_zoom_original)
		action_zoom_out.connect('activate', self.on_zoom_out)
		self.window.add_action(action_zoom_in)
		self.window.add_action(action_zoom_original)
		self.window.add_action(action_zoom_out)
		
		action_paginated = Gio.SimpleAction().new_stateful('md_prev_set_paginated', \
		None, GLib.Variant.new_boolean(False))
		action_paginated.connect('change-state', self.on_set_paginated)
		self.window.add_action(action_paginated)
		
		action_autoreload = Gio.SimpleAction().new_stateful('md_prev_set_autoreload', \
		None, GLib.Variant.new_boolean(self.auto_reload))
		action_autoreload.connect('change-state', self.on_set_reload)
		self.window.add_action(action_autoreload)
		
		action_panel = Gio.SimpleAction().new_stateful('md_prev_panel', \
		GLib.VariantType.new('s'), GLib.Variant.new_string(self._settings.get_string('position')))
		action_panel.connect('change-state', self.on_change_panel_from_popover)
		self.window.add_action(action_panel)
		
		action_hide = Gio.SimpleAction(name='md_prev_hide')
		action_hide.connect('activate', self.on_hide_panel)
		self.window.add_action(action_hide)
		
	def build_preview_ui(self):
		# This is the preview itself
		self._webview = WebKit2.WebView()
		self._webview.connect('context-menu', self.on_context_menu)
		
		searchBtn = self.build_search_popover()
		
		menuBtn = Gtk.MenuButton()
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menu.ui'))
		builder.set_translation_domain('gedit-plugin-markdown-preview') # ?????? FIXME
		self.menu_popover = Gtk.Popover().new_from_model(menuBtn, builder.get_object('preview-menu'))
		menuBtn.set_image(Gtk.Image().new_from_icon_name('view-more-symbolic', Gtk.IconSize.BUTTON))
		menuBtn.set_popover(self.menu_popover)
		
		# Building the interface
		self.pages_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		
		self.buttons_main_box = Gtk.Box(margin_left=5, margin_right=5, margin_top=5, margin_bottom=5, spacing=2)
		self.buttons_main_box.props.homogeneous = False
		self.pages_box.get_style_context().add_class('linked')

		refreshBtn = Gtk.Button().new_from_icon_name('view-refresh-symbolic', Gtk.IconSize.BUTTON)
		refreshBtn.connect('clicked', self.on_reload)

		previousBtn = Gtk.Button().new_from_icon_name('go-previous-symbolic', Gtk.IconSize.BUTTON)
		previousBtn.connect('clicked', self.on_previous_page)
		
		nextBtn = Gtk.Button().new_from_icon_name('go-next-symbolic', Gtk.IconSize.BUTTON)
		nextBtn.connect('clicked', self.on_next_page)
		self.pages_box.add(previousBtn)
		self.pages_box.add(nextBtn)
		
		self.warning_icon = Gtk.Image().new_from_icon_name('dialog-warning-symbolic', Gtk.IconSize.BUTTON)
		
		refreshBtn.set_tooltip_text(_("Reload the preview"))
		previousBtn.set_tooltip_text(_("Previous page"))
		nextBtn.set_tooltip_text(_("Next page"))
		searchBtn.set_tooltip_text(_("Search"))
		menuBtn.set_tooltip_text(_("More options"))
		
		self.buttons_main_box.pack_end(menuBtn, expand=False, fill=False, padding=0)
		self.buttons_main_box.pack_end(searchBtn, expand=False, fill=False, padding=0)
		self.buttons_main_box.pack_start(refreshBtn, expand=False, fill=False, padding=0)
		self.buttons_main_box.pack_start(self.pages_box, expand=False, fill=False, padding=0)
		self.buttons_main_box.pack_start(self.warning_icon, expand=False, fill=False, padding=2)

		# self.buttons_main_box only contains the buttons, it will pack at the end (bottom or right) of
		# the preview_bar object, where the webview has already been added.
		self.preview_bar.pack_end(self.buttons_main_box, expand=False, fill=False, padding=0)
		self.preview_bar.pack_start(self._webview, expand=True, fill=True, padding=0)
		
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
		action_reload_preview = Gio.SimpleAction(name='reload_preview') # FIXME action dupliquee inutilement
		reloadItem = WebKit2.ContextMenuItem.new_from_gaction(action_reload_preview, _("Reload the preview"), None)
		self.window.add_action(action_reload_preview)
		action_reload_preview.connect('activate', self.on_reload)
		b.append(reloadItem)
		return False
		
	def build_search_popover(self):
		some_damn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		
		searchBtn = Gtk.MenuButton()
		searchBtn.set_image(Gtk.Image().new_from_icon_name('system-search-symbolic', Gtk.IconSize.BUTTON))
		self._search_popover = Gtk.Popover()
		self._search_popover.set_relative_to(searchBtn)
		searchBtn.set_popover(self._search_popover)
		
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
		
		return searchBtn
		
	def on_change_panel_from_popover(self, *args):
		if GLib.Variant.new_string('bottom') == args[0].get_state():
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
			self.window.get_bottom_panel().set_property('visible', False)
		else:
			self.window.get_side_panel().set_property('visible', False)

	def on_set_paginated(self, *args):
		if not args[0].get_state():
			self.is_paginated = True
			self.pages_box.props.visible = True
			self.on_reload()
			args[0].set_state(GLib.Variant.new_boolean(True))
		else:
			self.is_paginated = False
			self.pages_box.props.visible = False
			self.on_reload()
			args[0].set_state(GLib.Variant.new_boolean(False))
	
	def on_previous_page(self, btn):
		if self.page_index > 0:
			self.page_index = self.page_index -1
			self.on_reload()
#		else:
#			btn.set_sensitive(False)
			
	def on_next_page(self, btn):
		self.page_index = self.page_index +1
		self.on_reload()
	
	def delete_temp_file(self):
		if self.temp_file_md.query_exists():
			self.temp_file_md.delete()
	
	def recognize_format(self):
		doc = self.window.get_active_document()
		# It will not load documents which are not .md/.html/.tex
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		self.display_warning(False, '')
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
		if self.page_index is len(html_pages):
			self.page_index = self.page_index -1
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
		self.preview_bar.show_all()
		self.panel.set_visible_child(self.preview_bar)
		self.pages_box.props.visible = self.is_paginated
		if self.window.get_state() is 'STATE_NORMAL':
			self.on_reload()

	def remove_from_panel(self):
		self.panel.remove(self.preview_bar)
	
	def on_zoom_in(self, *args):
		if self._webview.get_zoom_level() < 10:
			self._webview.set_zoom_level(self._webview.get_zoom_level() + 0.1)
		
	def on_zoom_out(self, *args):
		if self._webview.get_zoom_level() > 0.15:
			self._webview.set_zoom_level(self._webview.get_zoom_level() - 0.1)
			
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
	
	def change_panel(self, *args):
		self.remove_from_panel()
		self.show_on_panel()
		self.do_update_state()
		self.on_reload()
	
	def do_create_configure_widget(self):
		# Just return your box, PeasGtk will automatically pack it into a box and show it.
		widget = MdConfigWidget(self.plugin_info.get_data_dir())
		return widget

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
					subprocess.run(['pandoc', self.window.get_active_document().get_location().get_path(), \
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
		p = WebKit2.PrintOperation.new(self._webview)
		p.run_dialog()

############################

class MdConfigWidget(Gtk.Box):
	__gtype_name__ = 'MdConfigWidget'

	def __init__(self, datadir, **kwargs):
		super().__init__(**kwargs, orientation=Gtk.Orientation.VERTICAL,spacing=20, \
			margin_left=20,margin_right=20,margin_top=20,margin_bottom=20,homogeneous=True)
		
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		
		#--------
		positionSettingBox = Gtk.Box(spacing=20, orientation=Gtk.Orientation.HORIZONTAL)
		positionSettingBox.pack_start(Gtk.Label(_("Preview position")), expand=False, fill=False, padding=0)
		positionCombobox = Gtk.ComboBoxText()
		positionCombobox.append('side', _("Side Panel"))
		positionCombobox.append('bottom', _("Bottom Panel"))
		positionCombobox.set_active_id(self._settings.get_string('position'))
		positionCombobox.connect('changed', self.on_position_changed)
		positionSettingBox.pack_end(positionCombobox, expand=False, fill=False, padding=0)
		#--------
		relativePathsSettingBox = Gtk.Box(spacing=20, orientation=Gtk.Orientation.HORIZONTAL)
		relativePathsSettingBox.pack_start(Gtk.Label(_("Use relative paths")), expand=False, fill=False, padding=0)
		relativePathsSwitch = Gtk.Switch()
		relativePathsSwitch.set_state(self._settings.get_boolean('relative'))
		relativePathsSwitch.connect('notify::active', self.on_relative_changed)
		relativePathsSettingBox.pack_end(relativePathsSwitch, expand=False, fill=False, padding=0)
		#--------
		pdflatexSettingBox = Gtk.Box(spacing=20, orientation=Gtk.Orientation.HORIZONTAL)
		pdflatexSettingBox.pack_start(Gtk.Label(_("Export .tex files with pdflatex")), expand=False, fill=False, padding=0)
		pdflatexSwitch = Gtk.Switch()
		pdflatexSwitch.set_state(self._settings.get_boolean('pdflatex'))
		pdflatexSwitch.connect('notify::active', self.on_pdflatex_changed)
		pdflatexSettingBox.pack_end(pdflatexSwitch, expand=False, fill=False, padding=0)
		#--------
		styleSettingBox = Gtk.Box(spacing=20, orientation=Gtk.Orientation.HORIZONTAL)
		styleSettingBox.pack_start(Gtk.Label(_("Stylesheet")), expand=False, fill=False, padding=0)
		
		self.styleLabel = Gtk.Label()
		if len(self._settings.get_string('style')) >= 52:
			self.styleLabel.set_label("…" + self._settings.get_string('style')[-50:])
		else:
			self.styleLabel.set_label(self._settings.get_string('style'))
#		self.styleLabel = Gtk.Label(self._settings.get_string('style'))

		styleButton = Gtk.Button()
		styleButton.connect('clicked', self.on_choose_css)
		styleImage = Gtk.Image()
		styleImage.set_from_icon_name('document-open-symbolic', Gtk.IconSize.BUTTON)
		styleButton.add(styleImage)
		styleSettingBox.pack_end(styleButton, expand=False, fill=False, padding=0)
		styleSettingBox.pack_end(self.styleLabel, expand=False, fill=False, padding=0)
		#--------
		self.add(positionSettingBox)
		self.add(relativePathsSettingBox)
		self.add(pdflatexSettingBox)
		self.add(styleSettingBox)
		
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
	
