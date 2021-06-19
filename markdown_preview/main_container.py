# main_container.py
# GPL v3

import subprocess, gi, os
from gi.repository import Gtk, Gio, GLib
from .utils import get_backends_dict, init_gettext
from .webview_manager import MdWebViewManager
from .constants import MD_PREVIEW_KEY_BASE, MARKDOWN_SPLITTERS, BASE_TEMP_NAME

AVAILABLE_BACKENDS = get_backends_dict()
if AVAILABLE_BACKENDS['p3md']:
	import markdown

_ = init_gettext()

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

################################################################################

class MdMainContainer(Gtk.Box):
	__gtype_name__ = 'MdMainContainer'

	def __init__(self, parent_plugin, **kwargs):
		super().__init__(**kwargs)
		self.auto_reload = False
		self.parent_plugin = parent_plugin
		self.file_format = 'error'
		self._reload_is_locked = False

		# Where the values of settings will be loaded later
		self._active_backend = 'python'
		self._stylesheet = ''
		self._p3md_extensions = []
		self._pandoc_command = []

	def do_activate(self):
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self._handlers = [
			self._settings.connect('changed::position', self._update_container_position),
			self._settings.connect('changed::auto-manage-pane', self.set_auto_manage),
			self._settings.connect('changed::splitter', self.change_splitter_setting),

			self._settings.connect('changed::backend', self._on_backend_change),
			self._settings.connect('changed::pandoc-command', self._on_backend_change),
			self._settings.connect('changed::extension', self._on_backend_change),

			self._settings.connect('changed::style', self._on_stylesheet_change),
		]

		self.pagination_mode = self._settings.get_string('splitter')
		self.set_auto_manage()
		self.build_preview_ui()
		self.page_index = 0
		self.page_number = 1
		self.temp_file_md = Gio.File.new_for_path(BASE_TEMP_NAME + '.md')
		self.fix_backend_setting()

	def fix_backend_setting(self):
		if not AVAILABLE_BACKENDS['p3md'] and not AVAILABLE_BACKENDS['pandoc']:
			self._display_warning(_("Error: please install pandoc or python3-markdown"))
		elif not AVAILABLE_BACKENDS['p3md']:
			self._settings.set_string('backend', 'pandoc')
		elif not AVAILABLE_BACKENDS['pandoc']:
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
		# XXX if it's useful, do this elsewhere
		self._webview_manager.disconnect_handlers()
		self._settings.disconnect(self._handlers[6])
		self._settings.disconnect(self._handlers[5])
		self._settings.disconnect(self._handlers[4])
		self._settings.disconnect(self._handlers[3])
		self._settings.disconnect(self._handlers[2])
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

	def change_splitter_setting(self, *args):
		action = self.parent_plugin.window.lookup_action('md-set-view-mode')
		action.change_state(GLib.Variant.new_string(self._settings.get_string('splitter')))

	def change_splitter_action(self, *args):
		mode = args[1].get_string()
		self.set_pagination_mode(mode)
		args[0].set_state(GLib.Variant.new_string(mode))

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
		self._webview_manager.print_webview()

	############################################################################
	# Keep settings as attributes instead of querying GSettings too much #######

	def _on_stylesheet_change(self, *args):
		# maybe validate it?
		self._stylesheet = self._settings.get_string('style')

	def _on_backend_change(self, *args):
		self._active_backend = self._settings.get_string('backend')
		if self._active_backend == 'python':
			self._validate_p3md_extensions()
		else:
			self._validate_pandoc_command()
		self.on_reload()

	def _validate_p3md_extensions(self):
		# https://github.com/Python-Markdown/markdown/wiki/Third-Party-Extensions
		initial_md_extensions = self._settings.get_strv('extensions')
		final_md_extensions = []
		for extension in initial_md_extensions:
			try:
				markdown.markdown("test", extensions=[extension])
				final_md_extensions.append(extension)
			except Exception:
				self._display_warning(_("The extension '%s' isn't valid") % extension)
		self._settings.set_strv('extensions', final_md_extensions)
		self._p3md_extensions = final_md_extensions

	def _validate_pandoc_command(self):
		pandoc_command = self._settings.get_strv('pandoc-command')
		if '$INPUT_FILE' not in pandoc_command:
			pandoc_command.append('-s')
			pandoc_command.append('$INPUT_FILE')
		self._pandoc_command = pandoc_command

	############################################################################

	def _close_warning(self, *args):
		self.notification_label.set_label('')
		self.info_bar.set_visible(False)

	def _display_warning(self, text):
		self.notification_label.set_label(text)
		self.info_bar.set_visible(True)
		# print(text)

	############################################################################

	def build_preview_ui(self):
		ui_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'preview.ui'))
		self.preview_bar = ui_builder.get_object('preview_bar')
		preview_box = ui_builder.get_object('preview_box')
		self.buttons_main_box = ui_builder.get_object('buttons_main_box')

		# This is the preview itself
		self._webview_manager = MdWebViewManager()
		webview = self._webview_manager._webview
		preview_box.pack_start(webview, expand=True, fill=True, padding=0)

		# Search popover
		self._webview_manager.add_find_manager(ui_builder)

		# Displaying error messages
		self.info_bar = ui_builder.get_object('info_bar')
		self.notification_label = ui_builder.get_object('notification_label')
		self.info_bar.connect('close', self._close_warning)
		self.info_bar.connect('response', self._close_warning)

		# Plugin's main menu
		menuBtn = ui_builder.get_object('menu_btn')
		menu_builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'menus.ui'))
		menuBtn.set_menu_model(menu_builder.get_object('md-preview-menu'))

		# Navigation between pages
		self.pages_box = ui_builder.get_object('pages_box')
		self.warning_icon = ui_builder.get_object('warning_icon')
		previousBtn = ui_builder.get_object('previous_btn')
		nextBtn = ui_builder.get_object('next_btn')
		previousBtn.connect('clicked', self.on_previous_page)
		nextBtn.connect('clicked', self.on_next_page)

		self.show_on_panel()

	############################################################################

	def set_pagination_available(self, file_format):
		can_paginate = file_format == 'md'
		self.set_action_enabled('md-set-view-mode', can_paginate)
		if can_paginate:
			current_pagination = self.parent_plugin.window.lookup_action( \
			                        'md-set-view-mode').get_state().get_string()
			self.set_pagination_mode(current_pagination)
		else:
			self.set_is_whole_doc(False)

	def set_pagination_mode(self, mode):
		self.pagination_mode = mode
		is_whole = (self.pagination_mode == 'whole')
		self.set_is_whole_doc(is_whole)
		self.on_reload()

	def set_is_whole_doc(self, is_whole):
		self.set_action_enabled('md-prev-next', not is_whole)
		self.set_action_enabled('md-prev-previous', not is_whole)
		self.pages_box.props.visible = not is_whole

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
		if self.parent_plugin._auto_position:
			self.auto_change_panel()

		# Guard clause: it will not load documents if they're not a known format
		# or if the panel is not even visible
		if self.file_format == 'error' or not self.preview_bar.props.visible:
			return

		# Guard clause: it will not load documents if the panel is already used
		# for something else
		if self.panel.get_visible_child() != self.preview_bar:
			return

		if self._reload_is_locked:
			return
		self._reload_is_locked = True
		GLib.timeout_add(300, self._unlock_reload, {})
		self._on_reload_unsafe()

	def _unlock_reload(self, content_params):
		self._reload_is_locked = False
		self._on_reload_unsafe()

	def _on_reload_unsafe(self):
		"""Must be called ONLY by `on_reload` which checks pre-conditions, or by
		`_unlock_reload` which is called only by `on_reload` itself."""
		html_content = ''
		doc = self.parent_plugin.window.get_active_document()
		if doc is None:
			print("The window doesn't have any active document to preview")
			return
		if self.file_format == 'error':
			# The clause guard has to be duplicated because the document might
			# change during the delay between `on_reload` & `_on_reload_unsafe`
			return
		start, end = doc.get_bounds()
		unsaved_text = doc.get_text(start, end, True)
		unsaved_text = unsaved_text.encode('utf-8').decode()
		if self.file_format == 'html':
			html_content = self.get_html_from_html(unsaved_text)
		elif self._active_backend == 'python':
			html_content = self.get_html_from_p3md(unsaved_text)
		else:
			html_content = self.get_html_from_pandoc(unsaved_text)

		# The html code is converted into bytes
		my_string = GLib.String()
		my_string.append(html_content)
		bytes_content = my_string.free_to_bytes()

		# This uri will be used as a reference for links and images using
		# relative paths. It might not be related to the current file.
		dummy_uri = self.get_dummy_uri()
		self._webview_manager.load_bytes_for_uri(bytes_content, dummy_uri)

	def get_html_from_html(self, unsaved_text):
		# CSS not applied if it's HTML
		return self.current_page(unsaved_text, None)

	def get_html_from_pandoc(self, unsaved_text, from_temp_file=True):
		command = self._pandoc_command.copy()

		# Get the current document, or the temporary document if requested
		unsaved_text = self.current_page(unsaved_text, MARKDOWN_SPLITTERS)
		if from_temp_file:
			try:
				f = open(BASE_TEMP_NAME + '.md', 'w')
				f.write(unsaved_text)
				f.close()
			except UnicodeEncodeError as utf8_error:
				# The locale encoding sucks? Let's try with UTF-8
				f = open(BASE_TEMP_NAME + '.md', 'w', encoding='UTF-8')
				f.write(unsaved_text)
				f.close()
			except Exception as err:
				self._display_warning(_("Rendering error"))
				raise err
			f.close()
			file_path = self.temp_file_md.get_path()
		else: # in the future, other formats might be supported
			doc = self.parent_plugin.window.get_active_document()
			file_path = doc.get_uri_for_display()
		# XXX il est pas caché ce con là ??
		if '-c' not in command and self._settings.get_boolean('use-style'):
			command.append('-c')
			command.append(self._stylesheet)

		# Use pandoc to produce the html code
		command[command.index('$INPUT_FILE')] = file_path
		result = subprocess.run(command, stdout=subprocess.PIPE)
		html_content = result.stdout.decode('utf-8')
		return html_content

	def get_html_from_p3md(self, unsaved_text):
		unsaved_text = self.current_page(unsaved_text, MARKDOWN_SPLITTERS)
		if not self._settings.get_boolean('use-style'):
			pre_string = '<html><head><meta charset="utf-8" /></head><body>'
		else:
			pre_string = '<html><head><meta charset="utf-8" /><link ' + \
			  'rel="stylesheet" href="' + self._stylesheet + '" /></head><body>'
		post_string = '</body></html>'

		html_string = markdown.markdown(
			unsaved_text,
			extensions=self._p3md_extensions
		)
		html_content = pre_string + html_string + post_string
		return html_content

	############################################################################

	def on_file_changed(self, *args):
		self.file_format = self.recognize_format()
		self._update_panel_visibility()
		if self.file_format != 'error':
			self.on_reload()

	def recognize_format(self):
		doc = self.parent_plugin.window.get_active_document()
		# It will not load documents which are not .md/.html/.tex
		name = doc.get_short_name_for_display()
		temp = name.split('.')[-1]
		ret = None
		if temp == 'md':
			ret = 'md'
		elif temp == 'html':
			ret = 'html'

		if ret is None:
			if doc.is_untitled():
				self._display_warning(_("Can't preview an unsaved document"))
				# XXX it should
			else:
				self._display_warning(_("Unsupported type of document: ") + name)
			ret = 'error'
		else:
			self._close_warning()

			# Most accesses to GSettings are cached here
			self._on_backend_change()
			self._on_stylesheet_change()
		self.set_pagination_available(ret)
		# print(ret)
		return ret

	def current_page(self, lang_string, splitters_array):
		if self.pagination_mode == 'whole' or splitters_array == None:
			return lang_string
		else:
			correct_splitter = splitters_array[self.pagination_mode]

		# The document is (as much as possible) splitted in its original
		# language (md or html). It avoids converting some markdown to html
		# which wouldn't be rendered anyway.
		lang_pages = lang_string.split(correct_splitter)
		self.page_number = len(lang_pages)
		if self.page_index >= self.page_number:
			self.page_index = self.page_number - 1
			# TODO remember the page index in the Gedit.View objects
		lang_current_page = lang_pages[self.page_index]

		if self.page_index == 0:
			pass
		elif self.pagination_mode != 'hr':
			lang_current_page = correct_splitter + lang_current_page
		return lang_current_page

	def get_dummy_uri(self):
		# Support for relative paths is cool, but breaks CSS in many cases
		doc_location = None
		if self._settings.get_boolean('relative'):
			doc_location = self.parent_plugin.window.get_active_document().get_file().get_location()
		if doc_location is None:
			return 'file://'
		else:
			return doc_location.get_uri()

	############################################################################
	# Panels ###################################################################

	def auto_change_panel(self):
		position = self.get_wanted_position()
		window = self.parent_plugin.window
		# Get the bottom bar (a Gtk.Stack), or the side bar, and add our box to it.
		if position == 'bottom' and self.panel != window.get_bottom_panel():
			self._update_container_position()
			if self.auto_manage_panel:
				window.get_side_panel().hide()
		elif position == 'side' and self.panel != window.get_side_panel():
			self._update_container_position()
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
		# Get the bottom bar (a Gtk.Stack), or the side bar, and add our box to it.
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
		self._close_warning() # because the `show_all` shouldn't show that
		self.pages_box.props.visible = (self.pagination_mode != 'whole')
		if self.parent_plugin.window.get_state() == 'STATE_NORMAL':
			self.on_reload()

	def remove_from_panel(self):
		if self.panel is not None:
			self.panel.remove(self.preview_bar)

	def _update_container_position(self, *args):
		self.remove_from_panel()
		self.show_on_panel()
		self.do_update_state()
		self.on_reload()
		self._update_panel_visibility()

	def _update_panel_visibility(self):
		if not self.auto_manage_panel or self.file_format == 'error':
			if self.panel.props.visible:
				if self.panel.get_visible_child() == self.preview_bar:
					self.panel.hide()
		else:
			self.panel.show()

	############################################################################
################################################################################

