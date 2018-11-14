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
		self.parent_plugin = parent_plugin
		self.file_format = 'error'

	def do_activate(self):
		self._handlers = []
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self._handlers.append( self._settings.connect('changed::position', self.change_panel) )
		self._handlers.append( self._settings.connect('changed::auto-manage-panel', self.set_auto_manage) )
		self.is_paginated = False
		self.set_auto_manage()
#		self.connect_preview_menu()
		self.build_preview_ui()
		self.page_index = 0
		self.page_number = 1
		self.temp_file_md = Gio.File.new_for_path(BASE_TEMP_NAME + '.md')

	# This is called every time the gui is updated
	def do_update_state(self):
		if not self.panel.props.visible:
			return
		if self.parent_plugin.window.get_active_view() is not None:
			if self.auto_reload:
				self.on_reload()

	def do_deactivate(self):
		self._settings.disconnect(self._handlers[1])
		self._settings.disconnect(self._handlers[0])
		self.delete_temp_file()
		self.remove_from_panel()
		self.preview_bar.destroy()
		
	def set_auto_manage(self, *args):
		self.auto_manage_panel = self._settings.get_boolean('auto-manage-panel')

	def build_preview_ui(self):
		ui_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'preview.ui'))
		self.preview_bar = ui_builder.get_object('preview_bar')

		# This is the preview itself
		self._webview = WebKit2.WebView()
		self._webview.connect('context-menu', self.on_context_menu)
		self.preview_bar.pack_start(self._webview, expand=True, fill=True, padding=0)

		# Building UI elements
		menuBtn = ui_builder.get_object('menu_btn')
		menu_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menus.ui'))
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
		reloadItem = WebKit2.ContextMenuItem.new_from_gaction(self.parent_plugin.action_reload_preview, _("Reload the preview"), None)
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

	def on_set_reload(self, *args):
		if not args[0].get_state():
			self.auto_reload = True
			self.on_reload()
			args[0].set_state(GLib.Variant.new_boolean(True))
		else:
			self.auto_reload = False
			args[0].set_state(GLib.Variant.new_boolean(False))
		self._settings.set_boolean('auto-reload', self.auto_reload)

	def on_set_paginated(self, *args):
		if not args[0].get_state():
			self.is_paginated = True
			self.parent_plugin.window.lookup_action('md-prev-next').set_enabled(True)
			self.parent_plugin.window.lookup_action('md-prev-previous').set_enabled(True)
			self.pages_box.props.visible = True
			self.on_reload()
			args[0].set_state(GLib.Variant.new_boolean(True))
		else:
			self.is_paginated = False
			self.parent_plugin.window.lookup_action('md-prev-next').set_enabled(False)
			self.parent_plugin.window.lookup_action('md-prev-previous').set_enabled(False)
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

	def display_warning(self, visible, text):
		self.warning_icon.set_tooltip_text(text)
		self.warning_icon.props.visible = visible

	def update_visibility(self):
		if self.file_format == 'error' or not self.auto_manage_panel:
			if self._settings.get_string('position') == 'bottom':
				if len(self.panel.get_children()) is 1:
					self.panel.hide()
			else:
				if len(self.panel.get_children()) is 2:
					self.panel.hide()
			return
		else:
			self.panel.show()

	def on_reload(self, *args):
		# Guard clause: it will not load documents which are not .md
		if self.file_format == 'error' or not self.panel.props.visible:
			return

		html_content = ''
		if self.file_format == 'html':
			html_content = self.get_html_from_html()
		elif self.file_format == 'tex':
			html_content = self.get_html_from_tex()
		elif self._settings.get_string('backend') == 'python':
			html_content = self.get_html_from_md_python()
		else:
			html_content = self.get_html_from_md_pandoc()

		# The html code is converted into bytes
		my_string = GLib.String()
		my_string.append(html_content)
		bytes_content = my_string.free_to_bytes()

		# This uri will be used as a reference for links and images using relative paths
		dummy_uri = self.get_dummy_uri()

		self._webview.load_bytes(bytes_content, 'text/html', 'UTF-8', dummy_uri)
		
	def get_html_from_html(self):
		doc = self.parent_plugin.window.get_active_document()
		start, end = doc.get_bounds()
		html_string = doc.get_text(start, end, True)
		pre_string = '<html><head><meta charset="utf-8" /></head><body>'
		post_string = '</body></html>'
		html_string = self.current_page(html_string) # FIXME sous-optimal
		html_content = pre_string + html_string + post_string
		return html_content
	
	def get_html_from_tex(self):
		doc = self.parent_plugin.window.get_active_document()
		file_path = doc.get_location().get_path()

		# It uses pandoc to produce the html code
		pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
			self._settings.get_string('style') + '" /></head><body>'
		post_string = '</body></html>'
		result = subprocess.run(['pandoc', file_path], stdout=subprocess.PIPE)
		html_string = result.stdout.decode('utf-8')
		html_string = self.current_page(html_string, '<hr />')
		html_content = pre_string + html_string + post_string
		return html_content
		
	def get_html_from_md_pandoc(self):
		# Get the current document, or the temporary document if requested
		doc = self.parent_plugin.window.get_active_document()
		start, end = doc.get_bounds()
		unsaved_text = doc.get_text(start, end, True)
		unsaved_text = self.current_page(unsaved_text, '----')
		f = open(BASE_TEMP_NAME + '.md', 'w')
		f.write(unsaved_text)
		f.close()
		file_path = self.temp_file_md.get_path()

		# It uses pandoc to produce the html code
		pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
			self._settings.get_string('style') + '" /></head><body>'
		post_string = '</body></html>'
		result = subprocess.run(['pandoc', file_path], stdout=subprocess.PIPE)
		html_string = result.stdout.decode('utf-8')
		html_string = self.current_page(html_string, '<hr />')
		html_content = pre_string + html_string + post_string
		return html_content
		
	def get_html_from_md_python(self):
		doc = self.parent_plugin.window.get_active_document()
		start, end = doc.get_bounds()
		unsaved_text = doc.get_text(start, end, True)
		unsaved_text = self.current_page(unsaved_text, '----')
#		md_extensions = ['extra', 'sane_lists', 'toc', 'codehilite', 'admonition'] # TODO il y a une dpendance pour codehilite
		# TODO https://github.com/Python-Markdown/markdown/wiki/Third-Party-Extensions omgggg
		md_extensions = self._settings.get_strv('extensions')
		pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
			self._settings.get_string('style') + '" /></head><body>'
		post_string = '</body></html>'
		html_string = markdown.markdown(unsaved_text, extensions=md_extensions)
		html_content = pre_string + html_string + post_string
		return html_content

	def current_page(self, lang_string, splitter):
		if not self.is_paginated:
			return lang_string
		lang_pages = lang_string.split(splitter)
		self.page_number = len(lang_pages)
		if self.page_index >= self.page_number:
			self.page_index = self.page_number-1
		lang_current_page = lang_pages[self.page_index]
		return lang_current_page

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

##################################################
