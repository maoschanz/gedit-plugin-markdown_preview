# preview.py
# GPL v3

import subprocess, gi, os

BACKEND_P3MD_AVAILABLE = True
BACKEND_PANDOC_AVAILABLE = True
try:
	import markdown
except Exception:
	print("Package python3-markdown not installed")
	BACKEND_P3MD_AVAILABLE = False

try:
	status = subprocess.call(['which', 'pandoc'])
	assert(status == 0)
except Exception:
	print("Package pandoc not installed")
	BACKEND_PANDOC_AVAILABLE = False

gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, Gio, WebKit2, GLib

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	import gettext
	gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
	gettext.textdomain('gedit-plugin-markdown-preview')
	_ = gettext.gettext
except:
	_ = lambda s: s

MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'
BASE_TEMP_NAME = '/tmp/gedit_plugin_markdown_preview'

MARKDOWN_SPLITTERS = ['\n----', '\n# ', '\n## ']
HTML_SPLITTERS = ['<hr />', '<h1>', '<h2>']

################################################################################

class MdPreviewBar(Gtk.Box):
	__gtype_name__ = 'MdPreviewBar'

	def __init__(self, parent_plugin, **kwargs):
		super().__init__(**kwargs)
		self.auto_reload = False
		self.parent_plugin = parent_plugin
		self.file_format = 'error'
		self.scroll_level = 0

	def do_activate(self):
		self._handlers = []
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		id0 = self._settings.connect('changed::position', self.change_panel)
		id1 = self._settings.connect('changed::auto-manage-pane', self.set_auto_manage)
		self._handlers.append(id0)
		self._handlers.append(id1)
		self.pagination_mode = 'whole'
		self.set_auto_manage()
		self.build_preview_ui()
		self.page_index = 0
		self.page_number = 1
		self.temp_file_md = Gio.File.new_for_path(BASE_TEMP_NAME + '.md')
		self.fix_backend_setting()

	def fix_backend_setting(self):
		if not BACKEND_P3MD_AVAILABLE and not BACKEND_PANDOC_AVAILABLE:
			self.display_warning(_("Error: please install pandoc or python3-markdown"))
		elif not BACKEND_P3MD_AVAILABLE:
			self._settings.set_string('backend', 'pandoc')
		elif not BACKEND_PANDOC_AVAILABLE:
			self._settings.set_string('backend', 'python')

	# This is called every time the gui is updated
	def do_update_state(self):
		if not self.panel.props.visible:
			return
		elif self.panel.get_visible_child() != self.preview_bar:
			return
		if self.parent_plugin.window.get_active_view() is not None:
			if self.auto_reload:
				self.on_reload()

	def do_deactivate(self):
		self._webview.disconnect(self._handlers[4]) # XXX if it's useful, use this elsewhere
		self._webview.disconnect(self._handlers[3])
		self._webview.disconnect(self._handlers[2])
		self._settings.disconnect(self._handlers[1])
		self._settings.disconnect(self._handlers[0])
		self._delete_temp_file()
		self.remove_from_panel()
		self.preview_bar.destroy()

	def _delete_temp_file(self):
		if self.temp_file_md.query_exists():
			self.temp_file_md.delete()

	############################################################################
	# Misc #####################################################################

	def on_set_reload(self, *args):
		if not args[0].get_state():
			self.auto_reload = True
			self.on_reload()
			args[0].set_state(GLib.Variant.new_boolean(True))
		else:
			self.auto_reload = False
			args[0].set_state(GLib.Variant.new_boolean(False))
		self._settings.set_boolean('auto-reload', self.auto_reload)

	def set_auto_manage(self, *args):
		self.auto_manage_panel = self._settings.get_boolean('auto-manage-pane')

	def set_action_enabled(self, action_name, state):
		self.parent_plugin.window.lookup_action(action_name).set_enabled(state)

	def print_doc(self, *args):
		p = WebKit2.PrintOperation.new(self._webview)
		p.run_dialog()

	############################################################################

	def close_warning(self, *args):
		self.notification_label.set_label('')
		self.info_bar.set_visible(False)

	def display_warning(self, text):
		self.notification_label.set_label(text)
		self.info_bar.set_visible(True)

	############################################################################

	def build_preview_ui(self):
		ui_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'preview.ui'))
		self.preview_bar = ui_builder.get_object('preview_bar')
		preview_box = ui_builder.get_object('preview_box')
		self.buttons_main_box = ui_builder.get_object('buttons_main_box')

		# This is the preview itself
		self._webview = WebKit2.WebView()
		self._webview.get_settings().set_property('enable_javascript', True)
		id2 = self._webview.connect('context-menu', self.on_context_menu)
		id3 = self._webview.connect('mouse-target-changed', self.on_remember_scroll)
		id4 = self._webview.connect('load-changed', self.on_restore_scroll)
		self._handlers.append(id2)
		self._handlers.append(id3)
		self._handlers.append(id4)
		preview_box.pack_start(self._webview, expand=True, fill=True, padding=0)

		# Displaying error messages
		self.info_bar = ui_builder.get_object('info_bar')
		self.notification_label = ui_builder.get_object('notification_label')
		self.info_bar.connect('close', self.close_warning)
		self.info_bar.connect('response', self.close_warning)

		# Plugin's main menu
		menuBtn = ui_builder.get_object('menu_btn')
		menu_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menus.ui'))
		menuBtn.set_menu_model(menu_builder.get_object('md-preview-menu'))

		# Search popover
		search_entry = ui_builder.get_object('search_entry')
		search_entry.connect('search-changed', self.on_search_changed)

		ui_builder.get_object('up_btn').connect('clicked', self.on_search_up)
		ui_builder.get_object('down_btn').connect('clicked', self.on_search_down)

		self.find_controller = self._webview.get_find_controller()
		self.find_controller.connect('counted-matches', self.on_count_change)
		self.count_label = ui_builder.get_object('count_label')

		# Navigation between pages
		self.pages_box = ui_builder.get_object('pages_box')
		self.warning_icon = ui_builder.get_object('warning_icon')
		previousBtn = ui_builder.get_object('previous_btn')
		nextBtn = ui_builder.get_object('next_btn')
		previousBtn.connect('clicked', self.on_previous_page)
		nextBtn.connect('clicked', self.on_next_page)

		self.show_on_panel()

	############################################################################
	# Webview ##################################################################

	def on_remember_scroll(self, *args):
		js = 'window.document.body.scrollTop'
		self._webview.run_javascript(js, None, self.javascript_finished, None)
		return

	def on_restore_scroll(self, *args):
		js = 'window.document.body.scrollTop = ' + str(self.scroll_level) + '; undefined;'
		self._webview.run_javascript(js, None, None, None)
		return

	def javascript_finished(self, webview, result, user_data):
		js_result = webview.run_javascript_finish(result)
		if js_result is not None:
			value = js_result.get_js_value()
			if not value.is_undefined():
				self.scroll_level = value.to_int32()

	def build_context_item(self, name, gio_action):
		return WebKit2.ContextMenuItem.new_from_gaction(gio_action, name, None)

	def remove_at_position(self, context_menu, position):
		context_menu.remove( context_menu.get_item_at_position(position) )

	def on_context_menu(self, a, context_menu, c, hit_test_result):
		special_items = False
		openLinkWithItem = self.build_context_item(_("Open link in browser"), \
		                               self.parent_plugin.action_open_link_with)
		openImageWithItem = self.build_context_item(_("Open image in browser"), \
		                              self.parent_plugin.action_open_image_with)
		if hit_test_result.context_is_link() and hit_test_result.context_is_image():
			special_items = True
			self.remove_at_position(context_menu, 6) # save image as
			self.remove_at_position(context_menu, 5) # open image in a new window
			self.remove_at_position(context_menu, 2) # download link target
			self.remove_at_position(context_menu, 1) # open link in new window
			self.link_uri_to_open = hit_test_result.get_link_uri()
			self.image_uri_to_open = hit_test_result.get_image_uri()
			context_menu.insert(openLinkWithItem, 2)
			context_menu.insert(openImageWithItem, 6)
		elif hit_test_result.context_is_link():
			special_items = True
			self.remove_at_position(context_menu, 2) # download link target
			self.remove_at_position(context_menu, 1) # open link in new window
			self.link_uri_to_open = hit_test_result.get_link_uri()
			context_menu.append(openLinkWithItem)
		elif hit_test_result.context_is_image():
			special_items = True
			self.remove_at_position(context_menu, 0) # open image in a new window
			self.image_uri_to_open = hit_test_result.get_image_uri()
			context_menu.append(openImageWithItem)
		elif hit_test_result.context_is_selection():
			special_items = True

		context_menu.append(WebKit2.ContextMenuItem.new_separator())
		if not special_items:
			context_menu.remove_all()
		reloadItem = self.build_context_item(_("Reload the preview"), \
		                                       self.parent_plugin.action_reload)
		context_menu.append(reloadItem)
		return False

	def on_open_link_with(self, *args):
		Gtk.show_uri(None, self.link_uri_to_open, 0)

	def on_open_image_with(self, *args):
		Gtk.show_uri(None, self.image_uri_to_open, 0)

	############################################################################

	def on_set_paginated(self, mode):
		self.pagination_mode = mode
		is_whole = (self.pagination_mode == 'whole')
		self.set_action_enabled('md-prev-next', not is_whole)
		self.set_action_enabled('md-prev-previous', not is_whole)
		self.pages_box.props.visible = not is_whole
		self.on_reload()

	def on_previous_page(self, *args):
		if self.page_index > 0:
			self.page_index = self.page_index -1
			self.on_reload()

	def on_next_page(self, *args):
		self.page_index = self.page_index +1
		self.on_reload()

	############################################################################
	# Reload ###################################################################

	def on_reload(self, *args):
		# Guard clause: it will not load documents which are not supported
		self.file_format = self.recognize_format()
		if self.file_format == 'error' or not self.preview_bar.props.visible:
			return
		elif self.panel.get_visible_child() != self.preview_bar:
			return
		if self.parent_plugin._auto_position:
			self.auto_change_panel()

		css_uri = '' # TODO virer ça
		if self._settings.get_boolean('use-style'):
			css_uri = self._settings.get_string('style')

		html_content = ''
		doc = self.parent_plugin.window.get_active_document()
		start, end = doc.get_bounds()
		unsaved_text = doc.get_text(start, end, True)
		if self.file_format == 'html':
			html_content = self.get_html_from_html(unsaved_text)
		elif self._settings.get_string('backend') == 'python' \
		                                           and self.file_format == 'md':
			html_content = self.get_html_from_p3md(unsaved_text, css_uri)
		else:
			is_tex = self.file_format != 'tex'
			html_content = self.get_html_from_pandoc(unsaved_text, is_tex)

		# The html code is converted into bytes
		my_string = GLib.String()
		my_string.append(html_content)
		bytes_content = my_string.free_to_bytes()

		# This uri will be used as a reference for links and images using relative paths
		dummy_uri = self.get_dummy_uri()
		self._webview.load_bytes(bytes_content, 'text/html', 'UTF-8', dummy_uri)

	def get_html_from_html(self, unsaved_text):
		# CSS not applied if it's HTML
		return self.current_page(unsaved_text, HTML_SPLITTERS)

	def get_html_from_pandoc_temp(self, unsaved_text, css_uri):
		# Get the current document, or the temporary document if requested
		unsaved_text = self.current_page(unsaved_text, MARKDOWN_SPLITTERS)
		f = open(BASE_TEMP_NAME + '.md', 'w')
		f.write(unsaved_text)
		f.close()
		file_path = self.temp_file_md.get_path()

		# It uses pandoc to produce the html code
		command = ['pandoc', '-s', file_path, '--metadata', 'pagetitle=Preview']
		if css_uri != '':
			command = command + ['-c', css_uri]
		result = subprocess.run(command, stdout=subprocess.PIPE)
		html_content = result.stdout.decode('utf-8')
		return html_content

	def get_html_from_pandoc(self, unsaved_text, from_temp_file):
		# Get the current document, or the temporary document if requested
		unsaved_text = self.current_page(unsaved_text, MARKDOWN_SPLITTERS)
		if from_temp_file:
			f = open(BASE_TEMP_NAME + '.md', 'w')
			f.write(unsaved_text)
			f.close()
			file_path = self.temp_file_md.get_path()
		else: # if a tex file is used
			doc = self.parent_plugin.window.get_active_document()
			file_path = doc.get_uri_for_display()

		# It uses pandoc to produce the html code
		command = self._settings.get_strv('pandoc-command')
		if not from_temp_file and '-f' not in command:
			command = command + ['-f', 'latex']
		command[command.index('$INPUT_FILE')] = file_path
		result = subprocess.run(command, stdout=subprocess.PIPE)
		html_content = result.stdout.decode('utf-8')
		return html_content

	def get_html_from_p3md(self, unsaved_text, css_uri):
		unsaved_text = self.current_page(unsaved_text, MARKDOWN_SPLITTERS)
		# https://github.com/Python-Markdown/markdown/wiki/Third-Party-Extensions
		md_extensions = self._settings.get_strv('extensions')
		if css_uri == '':
			pre_string = '<html><head><meta charset="utf-8" /></head><body>'
		else:
			pre_string = '<html><head><meta charset="utf-8" />' + \
			     '<link rel="stylesheet" href="' + css_uri + '" /></head><body>'
		post_string = '</body></html>'
		html_string = markdown.markdown(unsaved_text, extensions=md_extensions)
		html_content = pre_string + html_string + post_string
		return html_content

	############################################################################

	def on_file_changed(self, *args):
		self.file_format = self.recognize_format()
		self.update_visibility()
		if self.file_format != 'error':
			self.on_reload()

	def recognize_format(self):
		doc = self.parent_plugin.window.get_active_document()
		# It will not load documents which are not .md/.html/.tex
		name = doc.get_short_name_for_display()
		temp = name.split('.')[-1]
		if temp == 'md':
			self.close_warning()
			return 'md'
		elif temp == 'html':
			self.close_warning()
			return 'html'
		elif temp == 'tex' and BACKEND_PANDOC_AVAILABLE and \
		                                self._settings.get_boolean('tex-files'):
			self.close_warning()
			return 'tex'
		if doc.is_untitled():
			self.display_warning(_("Can't preview an unsaved document")) # XXX
		else:
			self.display_warning(_("Unsupported type of document: ") + name)
		return 'error'

	def current_page(self, lang_string, splitters_array):
		if self.pagination_mode == 'whole':
			return lang_string
		elif self.pagination_mode == 'h1':
			correct_splitter = splitters_array[1]
		elif self.pagination_mode == 'h2':
			correct_splitter = splitters_array[2]
		else: # self.pagination_mode == 'hr':
			correct_splitter = splitters_array[0]

		# The document is (as much as possible) splitted in its original
		# language. It avoids converting some markdown to html which wouldn't be
		# rendered anyway.
		lang_pages = lang_string.split(correct_splitter)
		self.page_number = len(lang_pages)
		if self.page_index >= self.page_number:
			self.page_index = self.page_number-1
			# TODO remember the page index in the Gedit.View object
		lang_current_page = lang_pages[self.page_index]

		if self.page_index == 0:
			pass
		elif self.pagination_mode == 'h1':
			lang_current_page = splitters_array[1] + lang_current_page
		elif self.pagination_mode == 'h2':
			lang_current_page = splitters_array[2] + lang_current_page
		return lang_current_page

	def get_dummy_uri(self):
		# Support for relative paths is cool, but breaks CSS in many cases
		if self._settings.get_boolean('relative'):
			return self.parent_plugin.window.get_active_document().get_location().get_uri()
		else:
			return 'file://'

	############################################################################
	# Panels ###################################################################

	def auto_change_panel(self):
		position = self.get_wanted_position()
		window = self.parent_plugin.window
		# Get the bottom bar (A Gtk.Stack), or the side bar, and add our box to it.
		if position == 'bottom' and self.panel != window.get_bottom_panel():
			self.change_panel()
			self.update_visibility()
			if self.auto_manage_panel:
				window.get_side_panel().hide()
		elif position == 'side' and self.panel != window.get_side_panel():
			self.change_panel()
			self.update_visibility()
			if self.auto_manage_panel:
				window.get_bottom_panel().hide()

	def get_wanted_position(self):
		position = self._settings.get_string('position')
		window = self.parent_plugin.window
		if position == 'auto':
			width = window.get_allocated_width()
			if width < 100:
				return 'side' # i hardcode that to have my terminal accessible
			ratio = width / window.get_allocated_height()
			if ratio > 1.2:
				position = 'side'
			else:
				position = 'bottom'
		return position

	def show_on_panel(self):
		position = self.get_wanted_position()
		# Get the bottom bar (A Gtk.Stack), or the side bar, and add our box to it.
		if position == 'bottom':
			self.panel = self.parent_plugin.window.get_bottom_panel()
			self.preview_bar.props.orientation = Gtk.Orientation.HORIZONTAL
			self.buttons_main_box.props.orientation = Gtk.Orientation.VERTICAL
		else: # if position == 'side':
			self.panel = self.parent_plugin.window.get_side_panel()
			self.preview_bar.props.orientation = Gtk.Orientation.VERTICAL
			self.buttons_main_box.props.orientation = Gtk.Orientation.HORIZONTAL
		self.panel.add_titled(self.preview_bar, 'markdown_preview', _("Markdown Preview"))
		self.panel.set_visible_child(self.preview_bar)
		self.preview_bar.show_all()
		self.pages_box.props.visible = (self.pagination_mode != 'whole')
		if self.parent_plugin.window.get_state() is 'STATE_NORMAL':
			self.on_reload()

	def remove_from_panel(self):
		if self.panel is not None:
			self.panel.remove(self.preview_bar)

	def change_panel(self, *args):
		self.remove_from_panel()
		self.show_on_panel()
		self.do_update_state()
		self.on_reload()

	def update_visibility(self):
		if not self.auto_manage_panel or self.file_format == 'error':
			if self.panel.props.visible:
				if self.panel.get_visible_child() == self.preview_bar:
					self.panel.hide()
		else:
			self.panel.show()

	############################################################################
	# Zoom #####################################################################

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

	############################################################################
	# Search ###################################################################

	def on_search_changed(self, *args):
		text = args[0].get_text()
		self.find_controller.count_matches(text, WebKit2.FindOptions.CASE_INSENSITIVE, 100)
		self.find_controller.search(text, WebKit2.FindOptions.CASE_INSENSITIVE, 100)

	def on_search_up(self, btn):
		self.find_controller.search_previous()

	def on_search_down(self, btn):
		self.find_controller.search_next()

	def on_count_change(self, find_ctrl, number):
		self.count_label.set_text(_("%s results") % number)

	############################################################################
################################################################################
