# rendering_settings.py
# GPL v3

import gi, os
from gi.repository import Gtk

from ..constants import HelpLabels, BackendsEnums
from ..utils import get_backends_dict

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	import gettext
	gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
	gettext.textdomain('gedit-plugin-markdown-preview')
	_ = gettext.gettext
except:
	_ = lambda s: s

################################################################################

class MdRevealjsSettings():
	def __init__(self, settings, parent_widget):
		self._settings = settings
		self.parent_widget = parent_widget

		builder = Gtk.Builder().new_from_file(BASE_PATH + '/revealjs_box.ui')
		self.full_widget = builder.get_object('revealjs_box')

		self.transitions_combobox = builder.get_object('transitions_combobox')
		self.fill_combobox(self.transitions_combobox, 'revealjs-transitions', \
		                                      BackendsEnums.RevealJSTransitions)
		self.theme_combobox = builder.get_object('theme_combobox')
		self.fill_combobox(self.theme_combobox, 'revealjs-theme', \
		                                           BackendsEnums.RevealJSThemes)

		self.slidenum_switch = builder.get_object('slide_number_switch')
		show_slide_num = self._settings.get_boolean('revealjs-slide-num')
		self.slidenum_switch.set_active(show_slide_num)
		self.slidenum_switch.connect('notify::active', self._on_slidenum_changed)

	def fill_combobox(self, combobox, setting_key, labels_dict):
		for choice in labels_dict:
			combobox.append(choice, labels_dict[choice])
		combobox.set_active_id(self._settings.get_string(setting_key))
		combobox.connect('changed', self._on_combobox_changed, setting_key)

	def _on_combobox_changed(self, combobox, setting_key):
		new_value = combobox.get_active_id()
		if setting_key == 'revealjs-theme':
			pass # TODO
		elif setting_key == 'revealjs-transitions':
			pass # TODO

	def _on_slidenum_changed(self, *args):
		pass

	############################################################################
################################################################################

class MdCssSettings():
	def __init__(self, settings, related_window, parent_widget):
		self._settings = settings
		self.related_window = related_window # might sadly be None
		self.parent_widget = parent_widget

		builder = Gtk.Builder().new_from_file(BASE_PATH + '/css_box.ui')
		self.full_widget = builder.get_object('css_box')

		file_chooser_btn_css = builder.get_object('file_chooser_btn_css')
		file_chooser_btn_css.connect('clicked', self._on_choose_css)
		self.style_label = builder.get_object('style_label')
		self.css_uri = self._settings.get_string('style')

		self.switch_css = builder.get_object('switch_css')
		css_is_active = self._settings.get_boolean('use-style')
		self.switch_css.set_active(css_is_active)
		self.switch_css.connect('notify::active', self._on_use_css_changed)
		self.css_sensitive_box = builder.get_object('css_sensitive_box')

		self._set_css_active(css_is_active)
		self._update_file_chooser_btn_label()

	def _set_css_active(self, css_is_active):
		self.css_sensitive_box.set_sensitive(css_is_active)

	def _on_use_css_changed(self, *args):
		css_is_active = args[0].get_state()
		self._set_css_active(css_is_active)
		self.parent_widget.update_css(css_is_active, self.css_uri)

	def _on_choose_css(self, *args):
		# Building a FileChooserDialog for the CSS file
		file_chooser = Gtk.FileChooserNative.new(_("Select a CSS file"), \
		                                         self.related_window,
		                                         Gtk.FileChooserAction.OPEN, \
		                                         _("Select"), _("Cancel"))
		onlyCSS = Gtk.FileFilter()
		onlyCSS.set_name(_("Stylesheet"))
		onlyCSS.add_mime_type('text/css')
		file_chooser.add_filter(onlyCSS)
		response = file_chooser.run()

		if response == Gtk.ResponseType.ACCEPT:
			self.css_uri = file_chooser.get_uri()
			self._update_file_chooser_btn_label()
			self.parent_widget.update_css(self.is_active(), self.css_uri)
		file_chooser.destroy()

	def _update_file_chooser_btn_label(self):
		label = self.css_uri
		if label == '':
			label = _("Select a CSS file")
		if len(label) > 45:
			label = '…' + label[-45:]
		self.style_label.set_label(label)

	def is_active(self):
		return self.switch_css.get_active()

	############################################################################
################################################################################

class MdBackendSettings():
	def __init__(self, label, settings, apply_to_settings, parent_widget):
		self._settings = settings
		self.parent_widget = parent_widget
		self.plugins = {}
		self.apply_to_settings = apply_to_settings

		builder = Gtk.Builder().new_from_file(BASE_PATH + '/backend_box.ui')
		self.full_widget = builder.get_object('backend_box')
		builder.get_object('combo_label').set_label(label)
		self.backend_stack = builder.get_object('backend_stack')
		backendCombobox = builder.get_object('backend_combobox')
		backendCombobox.append('python', "python3-markdown")
		backendCombobox.append('pandoc', "pandoc")
		active_backend = self._settings.get_string('backend')
		backendCombobox.set_active_id(active_backend)
		backendCombobox.connect('changed', self.on_backend_changed)
		self.set_correct_page(active_backend)

		# Load UI for the python3-markdown backend
		self.extensions_flowbox = builder.get_object('extensions_flowbox')
		self.load_plugins_list()
		builder.get_object('help_label_1').set_label(HelpLabels.P3mdExtensions1)
		builder.get_object('help_label_2').set_label(HelpLabels.P3mdExtensions2)
		builder.get_object('help_label_3').set_label(HelpLabels.P3mdExtensions3)
		self.p3md_extension_entry = builder.get_object('p3md_extension_entry')
		self.p3md_extension_entry.connect('icon-release', self.on_add_ext)
		self.p3md_extension_entry.connect('activate', self.on_add_ext)

		# Load UI for the pandoc backend
		self.pandoc_cli_entry = builder.get_object('pandoc_command_entry')
		self.pandoc_cli_help = builder.get_object('help_label_pandoc')
		self.pandoc_cli_help.set_label(HelpLabels.PandocGeneral)
		self.remember_button = builder.get_object('remember_button')
		self.remember_button.connect('clicked', self.on_remember)
		self.format_combobox = builder.get_object('format_combobox')
		self.format_combobox.connect('changed', self.on_pandoc_format_changed)

		AVAILABLE_BACKENDS = get_backends_dict()
		if not AVAILABLE_BACKENDS['p3md']:
			self.backend_stack.set_visible_child_name('backend_pandoc')
			builder.get_object('switcher_box').set_sensitive(False)
		elif not AVAILABLE_BACKENDS['pandoc']:
			self.backend_stack.set_visible_child_name('backend_python')
			builder.get_object('switcher_box').set_sensitive(False)
		else:
			self.backend_stack.set_visible_child_name('backend_' + active_backend)

	############################################################################

	def on_backend_changed(self, w):
		backend = w.get_active_id()
		if self.apply_to_settings:
			self._settings.set_string('backend', backend)
		self.set_correct_page(backend)
		if backend == 'python':
			self.parent_widget.set_command_for_format('html5')
		else:
			self.on_pandoc_format_changed(self.format_combobox)

	def set_correct_page(self, backend):
		self.backend_stack.set_visible_child_name('backend_' + backend)

	def get_active_backend(self):
		return self.backend_stack.get_visible_child_name()

	############################################################################
	# Pandoc backend options ###################################################

	def fill_pandoc_combobox(self, formats_dict):
		for file_format in formats_dict:
			self.format_combobox.append(file_format, formats_dict[file_format])

	def init_pandoc_combobox(self, default_id):
		self.format_combobox.set_active_id(default_id)

	def update_pandoc_combobox(self):
		self.on_pandoc_format_changed(self.format_combobox)

	def on_remember(self, *args):
		new_command = self.pandoc_cli_entry.get_buffer().get_text()
		if self.apply_to_settings:
			self._settings.set_string('custom-render', new_command)
		else:
			self._settings.set_string('custom-export', new_command)

	def set_pandoc_command(self, command):
		self.pandoc_cli_entry.get_buffer().set_text(command)

	def on_pandoc_format_changed(self, w):
		output_format = w.get_active_id()
		is_custom = output_format == 'custom'
		self.remember_button.set_sensitive(is_custom)
		self.pandoc_cli_entry.set_sensitive(is_custom)
		self.parent_widget.set_command_for_format(output_format)
		if is_custom:
			self.pandoc_cli_help.set_label(HelpLabels.PandocCustom)
		else:
			self.pandoc_cli_help.set_label(HelpLabels.PandocGeneral)

	############################################################################
	# python3-markdown backend options #########################################

	def add_plugin_checkbtn(self, plugin_id):
		if plugin_id in self.plugins:
			return
		if plugin_id in BackendsEnums.P3mdExtensions:
			name = BackendsEnums.P3mdExtensions[plugin_id]
			description = BackendsEnums.P3mdDescriptions[plugin_id]
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
		for plugin_id in BackendsEnums.P3mdExtensions:
			self.add_plugin_checkbtn(plugin_id)
		array = self._settings.get_strv('extensions')
		for plugin_id in array:
			self.add_plugin_checkbtn(plugin_id)
			self.plugins[plugin_id].set_active(True)
		self.extensions_flowbox.show_all()

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

	############################################################################
################################################################################

