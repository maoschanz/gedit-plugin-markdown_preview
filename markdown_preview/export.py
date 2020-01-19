# __init__.py
# GPL v3

import subprocess, gi, os
from gi.repository import Gtk, Gio

from .kb_acc_data import LABELS
from .kb_acc_data import SETTINGS_KEYS

MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'

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

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	import gettext
	gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
	gettext.textdomain('gedit-plugin-markdown-preview')
	_ = gettext.gettext
except:
	_ = lambda s: s

P3MD_PLUGINS = {
	'extra': "Extras",
	'toc': _("Table of content"),
	'codehilite': "CodeHilite",
	'nl2br': _("New Line To Break"),
	'smarty': "SmartyPants",
	'sane_lists': _("Sane Lists"),
	'admonition': "Admonition",
	'wikilinks': "WikiLinks"
}

P3MD_PLUGINS_DESCRIPTIONS = {
	'extra': _("A compilation of various extensions (Abbreviations, Attribute Lists, Definition Lists, Fenced Code Blocks, Footnotes, Tables)."),
	'toc': _("Shows a clickable table of content with the [TOC] tag."),
	'codehilite': _("Highlights your code with a correct syntax coloration (it needs to be set up and have some dependencies)."), # XXX et du coup, lesquelles?
	'nl2br': _("Adds a line break at each new line."),
	'smarty': _("Converts ASCII dashes, quotes and ellipses to their nice-looking equivalents."),
	'sane_lists': _("Alters the behavior of the lists syntax."),
	'admonition': _("Adds admonitions (notes, warnings, tips, …) with the !!! tag."),
	'wikilinks': _("Converts any [[bracketed]] word to a link.")
}

HELP_LABEL_1 = _("Aside of default extensions provided by the " + \
"python3-markdown package, you can <b>install</b> third-party extensions " + \
"using instructions provided by their respective authors.")

HELP_LABEL_2 = _("These third-party extensions are <b>not</b> Gedit " + \
"plugins, they extend python3-markdown.")

HELP_LABEL_3 = _("Next, to improve the preview of your markdown file with " + \
"the features of these extensions, please add their module names to the " + \
"list using the text entry and the '+' icon.")

PANDOC_FORMATS_FULL = {
	'beamer': _("LaTeX beamer slideshow (.tex)"),
	'docx': _("Microsoft Word (.docx)"),
	'html5': _("HTML5"),
	'latex': _("LaTeX (.tex)"),
	'odt': _("OpenOffice text document (.odt)"),
	'pdf': _("Portable Document Format (.pdf)"),
	'plain': _("plain text (.txt)"),
	'pptx': _("PowerPoint slideshow (.pptx)"),
	'rtf': _("Rich Text Format (.rtf)"),
	'revealjs': _("reveal.js slideshow (HTML with Javascript)"),
	'custom': _("Custom command line")
}

PANDOC_FORMATS_PREVIEW = {
	'html5': _("HTML5"),
	'revealjs': _("reveal.js slideshow (HTML with Javascript)"),
	'custom': _("Custom command line")
}

################################################################################

class MdCSSSettings():
	def __init__(self, settings, related_window, parent_widget):
		self._settings = settings
		self.related_window = related_window # might sadly be None
		self.parent_widget = parent_widget

		builder = Gtk.Builder().new_from_file(BASE_PATH + '/css_box.ui')
		self.full_widget = builder.get_object('css_box')

		self.switch_css = builder.get_object('switch_css')
		self.switch_css.connect('notify::active', self.on_css_changed)
		self.css_sensitive_box = builder.get_object('css_sensitive_box')

		file_chooser_btn_css = builder.get_object('file_chooser_btn_css')
		file_chooser_btn_css.connect('clicked', self.on_choose_css)
		self.style_label = builder.get_object('style_label')
		self.css_uri = self._settings.get_string('style')
		self.update_file_chooser_btn_label()

	def on_css_changed(self, w, a):
		self.css_sensitive_box.set_sensitive(w.get_state())
		self.parent_widget.update_css(self.css_uri)

	def on_choose_css(self, w):
		# Building a FileChooserDialog for the CSS file
		file_chooser = Gtk.FileChooserNative.new(_("Select a CSS file"), \
		                      self.related_window, Gtk.FileChooserAction.OPEN, \
		                                               _("Select"), _("Cancel"))
		onlyCSS = Gtk.FileFilter()
		onlyCSS.set_name(_("Stylesheet"))
		onlyCSS.add_mime_type('text/css')
		file_chooser.add_filter(onlyCSS)
		response = file_chooser.run()

		if response == Gtk.ResponseType.ACCEPT:
			self.css_uri = file_chooser.get_uri()
			self.update_file_chooser_btn_label()
			self.parent_widget.update_css(self.css_uri)
		file_chooser.destroy()

	def update_file_chooser_btn_label(self):
		label = self.css_uri
		if len(label) > 50:
			label = '…' + label[-50:]
		self.style_label.set_label(label)

	############################################################################
################################################################################

class MdBackendSettings():
	def __init__(self, label, settings, apply_to_settings):
		self._settings = settings
		self.plugins = {}
		self.apply_to_settings = apply_to_settings

		builder = Gtk.Builder().new_from_file(BASE_PATH + '/backend_box.ui')
		self.full_widget = builder.get_object('backend_box')
		builder.get_object('combo_label').set_label(label)
		self.backend_stack = builder.get_object('backend_stack')
		self.full_widget.show_all() # XXX ugly
		backendCombobox = builder.get_object('backend_combobox')
		backendCombobox.append('python', "python3-markdown")
		backendCombobox.append('pandoc', "pandoc")
		backendCombobox.set_active_id(self._settings.get_string('backend'))
		backendCombobox.connect('changed', self.on_backend_changed)
		self.set_correct_page(self._settings.get_string('backend'))

		# Load UI for the python3-markdown backend
		self.extensions_flowbox = builder.get_object('extensions_flowbox')
		self.load_plugins_list()
		builder.get_object('help_label_1').set_label(HELP_LABEL_1)
		builder.get_object('help_label_2').set_label(HELP_LABEL_2)
		builder.get_object('help_label_3').set_label(HELP_LABEL_3)
		self.p3md_extension_entry = builder.get_object('p3md_extension_entry')
		self.p3md_extension_entry.connect('icon-release', self.on_add_ext)
		self.p3md_extension_entry.connect('activate', self.on_add_ext)

		# Load UI for the pandoc backend
		self.pandoc_cli_entry = builder.get_object('pandoc_command_entry')
		self.remember_button = builder.get_object('remember_button')
		self.remember_button.connect('clicked', self.on_remember)
		self.format_combobox = builder.get_object('format_combobox')

		if not BACKEND_P3MD_AVAILABLE:
			self.backend_stack.set_visible_child_name('backend_pandoc')
			builder.get_object('switcher_box').set_visible(False)
		elif not BACKEND_PANDOC_AVAILABLE:
			self.backend_stack.set_visible_child_name('backend_python')
			builder.get_object('switcher_box').set_visible(False)
		else:
			active_backend = self._settings.get_string('backend')
			self.backend_stack.set_visible_child_name('backend_' + active_backend)

	def fill_pandoc_combobox(self, formats_dict, default_id):
		for file_format in formats_dict:
			self.format_combobox.append(file_format, formats_dict[file_format])
		self.format_combobox.set_active_id(default_id)

	def add_plugin_checkbtn(self, plugin_id):
		if plugin_id in self.plugins:
			return
		if plugin_id in P3MD_PLUGINS:
			name = P3MD_PLUGINS[plugin_id]
			description = P3MD_PLUGINS_DESCRIPTIONS[plugin_id]
		else:
			name = plugin_id
			description = None
		btn = Gtk.CheckButton(visible=True, label=name)
		if description is not None:
			btn.set_tooltip_text(description)
		self.plugins[plugin_id] = btn
		self.extensions_flowbox.add(btn)
		if self.apply_to_settings:
			btn.connect('clicked', self.update_plugins_list)

	def load_plugins_list(self, *args):
		for plugin_id in P3MD_PLUGINS:
			self.add_plugin_checkbtn(plugin_id)
		array = self._settings.get_strv('extensions')
		for plugin_id in array:
			self.add_plugin_checkbtn(plugin_id)
			self.plugins[plugin_id].set_active(True)
		self.extensions_flowbox.show_all()

	############################################################################

	def update_plugins_list(self, *args):
		array = []
		for plugin_id in self.plugins:
			if self.plugins[plugin_id].get_active():
				array.append(plugin_id)
		self._settings.set_strv('extensions', array)

	def on_add_ext(self, *args):
		plugin_id = self.p3md_extension_entry.get_text()
		self.add_plugin_checkbtn(plugin_id)
		self.plugins[plugin_id].set_active(True)
		self.p3md_extension_entry.set_text('')

	def on_backend_changed(self, w):
		backend = w.get_active_id()
		if self.apply_to_settings:
			self._settings.set_string('backend', backend)
		self.set_correct_page(backend)

	def set_correct_page(self, backend):
		self.backend_stack.set_visible_child_name('backend_' + backend)

	def get_active_backend(self):
		return self.backend_stack.get_visible_child_name()

	def on_remember(self, b):
		new_command = self.pandoc_command_entry.get_buffer().get_text()
		self._settings.set_string('custom-export', new_command)

	def set_pandoc_command(self, command):
		self.pandoc_cli_entry.get_buffer().set_text(command)

	############################################################################
################################################################################

class MdExportDialog(Gtk.Dialog):
	__gtype_name__ = 'MdExportDialog'

	file_format = 'md'
	output_extension = '.pdf'

	def __init__(self, file_format, gedit_window, settings, **kwargs):
		super().__init__(use_header_bar=True, title=_("Export as…"), **kwargs)
		self.file_format = file_format
		self.gedit_window = gedit_window
		self._settings = settings

		self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
		self.get_content_area().set_margin_left(20)
		self.get_content_area().set_margin_right(20)
		self.get_content_area().set_margin_top(20)
		self.get_content_area().set_margin_bottom(20)
		self.get_content_area().set_spacing(20)
		if not BACKEND_P3MD_AVAILABLE and not BACKEND_PANDOC_AVAILABLE:
			error_label = Gtk.Label(visible=True, \
			        label=_("Error: please install pandoc or python3-markdown"))
			self.get_content_area().add(error_label)
			return
		self.add_button(_("Next"), Gtk.ResponseType.OK)

		# Add the backend settings to the dialog
		self._backend = MdBackendSettings(_("Export file with:"), \
		                                                  self._settings, False)
		self.get_content_area().add(self._backend.full_widget)
		self._backend.fill_pandoc_combobox(PANDOC_FORMATS_FULL, 'pdf')

		self.get_content_area().add(Gtk.Separator(visible=True))

		# Using a stylesheet is possible with both backends
		self.css_manager = MdCSSSettings(self._settings, self, self)
		self.get_content_area().add(self.css_manager.full_widget)

		self.on_pandoc_format_changed(self._backend.format_combobox)
		self._backend.format_combobox.connect('changed', self.on_pandoc_format_changed)

	def do_cancel_export(self):
		self.destroy()

	############################################################################

	def update_css(self, uri):
		self.on_pandoc_format_changed(self._backend.format_combobox)

	def on_pandoc_format_changed(self, w):
		output_format = w.get_active_id()

		self._backend.remember_button.set_sensitive(output_format == 'custom')
		if output_format == 'custom':
			command = self._settings.get_string('custom-export')
			self._backend.set_pandoc_command(command)
			self.output_extension = '.pdf'
			return

		command = 'pandoc $INPUT_FILE %s -o $OUTPUT_FILE'
		options = ''
		accept_css = True
		if output_format == 'pdf':
			options = '-V geometry=right=2cm -V geometry=left=2cm -V ' \
			                 'geometry=bottom=2cm -V geometry=top=2cm'
			self.output_extension = '.pdf'
		elif output_format == 'revealjs':
			options = '-t revealjs -s -V revealjs-url=http://lab.hakim.se/reveal-js'
			# TODO slide numbers ??
			self.output_extension = '.html'
			# accept_css = False # XXX ?
		else:
			options = '-t ' + output_format
			if output_format == 'beamer' or output_format == 'latex':
				self.output_extension = '.tex'
				# accept_css = False # XXX ?
			elif output_format == 'html5':
				options = options + ' -s'
				self.output_extension = '.html'
			elif output_format == 'plain':
				self.output_extension = '.txt'
				accept_css = False
			else:
				self.output_extension = '.' + output_format
		if self.css_manager.switch_css.get_state() and accept_css:
			options = options + ' -c ' + self.css_manager.css_uri
		self._backend.set_pandoc_command(command % options)

	############################################################################
	# Export process ###########################################################

	def do_next(self):
		if self._backend.get_active_backend() == 'backend_python':
			exported = self.export_p3md()
		else: # if self._backend.get_active_backend() == 'backend_pandoc':
			exported = self.export_pandoc()
		self.destroy()

	def launch_file_chooser(self, output_extension):
		file_chooser = Gtk.FileChooserNative.new(_("Export the preview"), \
		                        self.gedit_window, Gtk.FileChooserAction.SAVE, \
		                                               _("Export"), _("Cancel"))
		name = self.gedit_window.get_active_document().get_short_name_for_display()
		# retirer l'ancienne extension ?
		name = str(name + ' ' + _("(exported)") + output_extension)
		file_chooser.set_current_name(name)
		file_chooser.set_do_overwrite_confirmation(True)
		response = file_chooser.run()
		if response == Gtk.ResponseType.ACCEPT:
			return file_chooser
		else:
			file_chooser.destroy()
			return None

	def export_p3md(self):
		file_chooser = self.launch_file_chooser('.html')
		if file_chooser is None:
			return False

		md_extensions = []
		for plugin_id in self._backend.plugins:
			if self._backend.plugins[plugin_id].get_active():
				md_extensions.append(plugin_id)

		doc = self.gedit_window.get_active_document()
		start, end = doc.get_bounds()
		unsaved_text = doc.get_text(start, end, True)
		content = markdown.markdown(unsaved_text, extensions=md_extensions)
		with open(file_chooser.get_filename(), 'w') as f:
			f.write(content)
		if self.css_manager.switch_css.get_active():
			pre_string = '<html><head><meta charset="utf-8" />' + \
			      '<link rel="stylesheet" href="' + self.css_manager.css_uri + \
			                                                 '" /></head><body>'
			post_string = '</body></html>'
			with open(file_chooser.get_filename(), 'r+') as f:
				content = f.read()
				f.seek(0, 0)
				f.write(pre_string.rstrip('\r\n') + '\n' + content)
			with open(file_chooser.get_filename(), 'a') as f:
				f.write(post_string)
		file_chooser.destroy()
		return True

	def export_pandoc(self):
		file_chooser = self.launch_file_chooser(self.output_extension)
		if file_chooser is None:
			return False

		output_format = self._backend.format_combobox.get_active_id()
		doc_path = self.gedit_window.get_active_document().get_location().get_path()
		buff = self._backend.pandoc_cli_entry.get_buffer()
		cmd = buff.get_text(buff.get_start_iter(), buff.get_end_iter(), False)
		words = cmd.split()
		words[words.index('$INPUT_FILE')] = doc_path
		words[words.index('$OUTPUT_FILE')] = file_chooser.get_filename()
		subprocess.run(words)
		file_chooser.destroy()
		return True

	############################################################################
################################################################################

class MdConfigWidget(Gtk.Box):
	__gtype_name__ = 'MdConfigWidget'

	def __init__(self, datadir, **kwargs):
		super().__init__(**kwargs, orientation=Gtk.Orientation.VERTICAL, \
		                                                  spacing=10, margin=10)
		# XXX what's datadir ??
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)

		builder = Gtk.Builder().new_from_file(BASE_PATH + '/prefs.ui')
#		builder.set_translation_domain('gedit-plugin-markdown-preview') # TODO
		stack = builder.get_object('stack')
		switcher = Gtk.StackSwitcher(stack=stack, halign=Gtk.Align.CENTER)

		### PREVIEW PAGE #######################################################

		preview_box = builder.get_object('preview_box')

		positionCombobox = builder.get_object('positionCombobox')
		positionCombobox.append('auto', _("Automatic"))
		positionCombobox.append('side', _("Side Panel"))
		positionCombobox.append('bottom', _("Bottom Panel"))
		positionCombobox.set_active_id(self._settings.get_string('position'))
		positionCombobox.connect('changed', self.on_position_changed)

		relativePathsSwitch = builder.get_object('relativePathsSwitch')
		relativePathsSwitch.set_state(self._settings.get_boolean('relative'))
		relativePathsSwitch.connect('notify::active', self.on_relative_changed)

		autoManageSwitch = builder.get_object('autoManageSwitch')
		autoManageSwitch.set_state(self._settings.get_boolean('auto-manage-panel'))
		autoManageSwitch.connect('notify::active', self.on_auto_manage_changed)

		preview_box.add(Gtk.Separator(visible=True))

		self.css_manager = MdCSSSettings(self._settings, None, self)
		preview_box.add(self.css_manager.full_widget)

		### BACKEND PAGE #######################################################

		self._backend = MdBackendSettings(_("HTML generation backend:"), \
		                                                   self._settings, True)
		builder.get_object('backend_box').add(self._backend.full_widget)
		self._backend.fill_pandoc_combobox(PANDOC_FORMATS_PREVIEW, 'html5')
		self.on_pandoc_format_changed(self._backend.format_combobox)
		self._backend.format_combobox.connect('changed', self.on_pandoc_format_changed)

		### SHORTCUTS PAGE #####################################################

		self.shortcuts_treeview = builder.get_object('shortcuts_treeview')
		renderer = builder.get_object('accel_renderer')
		renderer.connect('accel-edited', self.on_accel_edited)
		renderer.connect('accel-cleared', self.on_accel_cleared)
#		https://github.com/GNOME/gtk/blob/master/gdk/keynames.txt
		for i in range(len(SETTINGS_KEYS)):
			self.add_keybinding(SETTINGS_KEYS[i], LABELS[i])
		self.add(switcher)
		self.add(stack)

	############################################################################

	def add_keybinding(self, setting_id, description):
		accelerator = self._settings.get_strv(setting_id)[0]
		if accelerator is None:
			[key, mods] = [0, 0]
		else:
			[key, mods] = Gtk.accelerator_parse(accelerator)
		row_array = [setting_id, description, key, mods]
		row = self.shortcuts_treeview.get_model().insert(0, row=row_array)

	def on_accel_edited(self, *args):
		tree_iter = self.shortcuts_treeview.get_model().get_iter_from_string(args[1])
		self.shortcuts_treeview.get_model().set(tree_iter, [2, 3], [args[2], int(args[3])])
		setting_id = self.shortcuts_treeview.get_model().get_value(tree_iter, 0)
		accelString = Gtk.accelerator_name(args[2], args[3])
		self._settings.set_strv(setting_id, [accelString])

	def on_accel_cleared(self, *args):
		tree_iter = self.shortcuts_treeview.get_model().get_iter_from_string(args[1])
		self.shortcuts_treeview.get_model().set(tree_iter, [2, 3], [0, 0])
		setting_id = self.shortcuts_treeview.get_model().get_value(tree_iter, 0)
		self._settings.set_strv(setting_id, [])

	############################################################################
	# Preview options ##########################################################

	def on_relative_changed(self, w, a):
		self._settings.set_boolean('relative', w.get_state())

	def on_position_changed(self, w):
		position = w.get_active_id()
		self._settings.set_string('position', position)

	def on_auto_manage_changed(self, w, a):
		self._settings.set_boolean('auto-manage-panel', w.get_state())

	def update_css(self, uri):
		self._settings.set_string('style', uri)
		self.on_pandoc_format_changed(self._backend.format_combobox)

	############################################################################
	# Backend management #######################################################

	def on_pandoc_format_changed(self, w):
		output_format = w.get_active_id()

		self._backend.remember_button.set_sensitive(output_format == 'custom')
		if output_format == 'custom':
			command = self._settings.get_string('custom-export')
			self._backend.set_pandoc_command(command)
			self.output_extension = '.pdf'
			return

		command = 'pandoc $INPUT_FILE %s -o $OUTPUT_FILE'
		options = ''
		accept_css = True
		# TODO........
		if self.css_manager.switch_css.get_state() and accept_css:
			options = options + ' -c ' + self.css_manager.css_uri
		self._backend.set_pandoc_command(command % options)

	############################################################################
################################################################################

