# rendering_settings.py
# GPL v3

import gi, os
from gi.repository import Gtk

from ..constants import HelpLabels, BackendsEnums
from ..utils import get_backends_dict, init_gettext

_ = init_gettext()

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

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

		self.backend_combobox = builder.get_object('backend_combobox')
		self.backend_combobox.append('python', "python3-markdown")
		self.backend_combobox.append('pandoc', "pandoc")
		active_backend = self._settings.get_string('backend')
		self.backend_combobox.set_active_id(active_backend)
		self.backend_combobox.connect('changed', self.on_backend_changed)
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
		pandoc_cli_help = builder.get_object('help_label_pandoc')
		pandoc_cli_help.set_label(HelpLabels.PandocGeneral)

		self.pandoc_cli_custom = builder.get_object('help_label_pandoc_custom')
		self.remember_button = builder.get_object('remember_button')
		if self.apply_to_settings:
			self.pandoc_cli_custom.set_label(HelpLabels.PandocCustom)
			remember_btn_label = _("Remember as custom rendering command")
		else:
			self.pandoc_cli_custom.set_label(HelpLabels.PandocExport)
			remember_btn_label = _("Remember as custom export command")
		self.remember_button.set_label(remember_btn_label)
		self.remember_button.connect('clicked', self.on_remember)

		self.format_combobox = builder.get_object('format_combobox')
		self.format_combobox.connect('changed', self.on_pandoc_format_changed)

		self._switcher_box = builder.get_object('switcher_box')
		AVAILABLE_BACKENDS = get_backends_dict()
		self.set_available_backends(AVAILABLE_BACKENDS, active_backend)

	############################################################################

	def set_available_backends(self, backends_dict, active_backend='pandoc'):
		self._switcher_box.set_visible(True)
		if not backends_dict['p3md']:
			self.backend_stack.set_visible_child_name('backend_pandoc')
			self._switcher_box.set_visible(False)
		elif not backends_dict['pandoc']:
			self.backend_stack.set_visible_child_name('backend_python')
			self._switcher_box.set_visible(False)
		else:
			self.backend_combobox.set_active_id(active_backend)
			self.set_correct_page(active_backend)

	def on_backend_changed(self, w):
		backend = w.get_active_id()
		if self.apply_to_settings:
			self._settings.set_string('backend', backend)
		self.set_correct_page(backend)
		if backend == 'pandoc':
			self.update_pandoc_combobox()

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
		self.adapt_widgets_to_pandoc_custom(default_id == 'custom')

	def update_pandoc_combobox(self, *args):
		self.on_pandoc_format_changed(self.format_combobox)

	def on_remember(self, *args):
		buff = self.pandoc_cli_entry.get_buffer()
		cmd = buff.get_text(buff.get_start_iter(), buff.get_end_iter(), False)
		if self.apply_to_settings:
			self._settings.set_string('custom-render', cmd)
		else:
			self._settings.set_string('custom-export', cmd)

	def set_pandoc_command(self, command):
		self.pandoc_cli_entry.get_buffer().set_text(command)

	def on_pandoc_format_changed(self, w):
		output_format = w.get_active_id()
		self.adapt_widgets_to_pandoc_custom(output_format == 'custom')
		self.parent_widget.set_command_for_format(output_format)

	def adapt_widgets_to_pandoc_custom(self, is_custom):
		if not self.apply_to_settings:
			is_custom = True
		self.pandoc_cli_entry.set_sensitive(is_custom)
		self.remember_button.set_visible(is_custom)
		self.pandoc_cli_custom.set_visible(is_custom)

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

