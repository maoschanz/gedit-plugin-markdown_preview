# prefs_dialog.py
# GPL v3

import gi, os
from gi.repository import Gtk, Gio

from .rendering_settings import MdCssSettings, MdBackendSettings
from ..utils import get_backends_dict
from ..constants import KeyboardShortcuts, HelpLabels, BackendsEnums, MD_PREVIEW_KEY_BASE

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

################################################################################

class MdConfigWidget(Gtk.Box):
	__gtype_name__ = 'MdConfigWidget'

	def __init__(self, datadir, **kwargs):
		super().__init__(**kwargs, orientation=Gtk.Orientation.HORIZONTAL)
		# print(datadir) # TODO c'est le path de là où est le plugin, ça peut
		# aider à mettre un css par défaut ?
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self._kb_settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE + '.keybindings')

		builder = Gtk.Builder().new_from_file(BASE_PATH + '/prefs.ui')
		# builder.set_translation_domain('gedit-plugin-markdown-preview') # FIXME
		stack = builder.get_object('stack')
		sidebar = Gtk.StackSidebar(stack=stack)

		self._build_general_page(builder)
		self._build_backend_page(builder)
		self._build_style_page(builder)
		self._backend.init_pandoc_combobox('html5') # TODO FIXME wrong, not what the user defined!!
		self._build_shortcuts_page(builder)

		self.add(sidebar)
		self.add(stack)

	def _build_general_page(self, builder):
		general_box = builder.get_object('general_box')

		positionCombobox = builder.get_object('positionCombobox')
		positionCombobox.append('auto', _("Automatic"))
		positionCombobox.append('side', _("Side Pane"))
		positionCombobox.append('bottom', _("Bottom Pane"))
		positionCombobox.set_active_id(self._settings.get_string('position'))
		positionCombobox.connect('changed', self.on_position_changed)

		autoManageSwitch = builder.get_object('autoManageSwitch')
		autoManageSwitch.set_state(self._settings.get_boolean('auto-manage-pane'))
		autoManageSwitch.connect('notify::active', self.on_auto_manage_changed)

		splitter_combobox = builder.get_object('splitter_combobox')
		splitter_combobox.append('hr', _("Split at separators"))
		splitter_combobox.append('whole', _("Whole document"))
		splitter_combobox.append('h1', _("Split at level 1 titles"))
		splitter_combobox.append('h2', _("Split at level 2 titles"))
		splitter_combobox.set_active_id(self._settings.get_string('splitter'))
		splitter_combobox.connect('changed', self.on_splitter_changed)

		########################################################################

		relative_paths_switch = builder.get_object('relative_paths_switch')
		relative_paths_switch.set_state(self._settings.get_boolean('relative'))
		relative_paths_switch.connect('notify::active', self.on_relative_changed)

	def _build_style_page(self, builder):
		style_box = builder.get_object('style_box')

		style_box.add(self._new_dim_label(HelpLabels.StyleCSS))
		self.css_manager = MdCssSettings(self._settings, None, self)
		style_box.add(self.css_manager.full_widget)

	def _build_backend_page(self, builder):
		self._backend = MdBackendSettings(_("HTML generation backend:"), \
		                                             self._settings, True, self)
		builder.get_object('backend_box').add(self._backend.full_widget)
		self._backend.fill_pandoc_combobox(BackendsEnums.PandocFormatsPreview)

	def _build_shortcuts_page(self, builder):
		self.shortcuts_treeview = builder.get_object('shortcuts_treeview')
		renderer = builder.get_object('accel_renderer')
		renderer.connect('accel-edited', self._on_accel_edited)
		renderer.connect('accel-cleared', self._on_accel_cleared)
		# https://github.com/GNOME/gtk/blob/master/gdk/keynames.txt
		for i in range(len(KeyboardShortcuts.SettingsKeys)):
			self._add_keybinding(KeyboardShortcuts.SettingsKeys[i], \
			                                        KeyboardShortcuts.Labels[i])

	############################################################################

	def _new_dim_label(self, raw_text):
		label = Gtk.Label(wrap=True, visible=True, label=raw_text, \
		                                                 halign=Gtk.Align.START)
		label.get_style_context().add_class('dim-label')
		return label

	def _add_keybinding(self, setting_id, description):
		accelerator = self._kb_settings.get_strv(setting_id)[0]
		if accelerator is None:
			[key, mods] = [0, 0]
		else:
			[key, mods] = Gtk.accelerator_parse(accelerator)
		row_array = [setting_id, description, key, mods]
		row = self.shortcuts_treeview.get_model().insert(0, row=row_array)

	def _on_accel_edited(self, *args):
		tree_iter = self.shortcuts_treeview.get_model().get_iter_from_string(args[1])
		self.shortcuts_treeview.get_model().set(tree_iter, [2, 3], [args[2], int(args[3])])
		setting_id = self.shortcuts_treeview.get_model().get_value(tree_iter, 0)
		accelString = Gtk.accelerator_name(args[2], args[3])
		self._kb_settings.set_strv(setting_id, [accelString])

	def _on_accel_cleared(self, *args):
		tree_iter = self.shortcuts_treeview.get_model().get_iter_from_string(args[1])
		self.shortcuts_treeview.get_model().set(tree_iter, [2, 3], [0, 0])
		setting_id = self.shortcuts_treeview.get_model().get_value(tree_iter, 0)
		self._kb_settings.set_strv(setting_id, [])

	############################################################################
	# Preview options ##########################################################

	def on_relative_changed(self, w, a):
		self._settings.set_boolean('relative', w.get_state())

	def on_position_changed(self, w):
		position = w.get_active_id()
		self._settings.set_string('position', position)

	def on_splitter_changed(self, w):
		splitter = w.get_active_id()
		self._settings.set_string('splitter', splitter)

	def on_auto_manage_changed(self, w, a):
		self._settings.set_boolean('auto-manage-pane', w.get_state())

	def update_css(self, is_active, uri):
		self._settings.set_boolean('use-style', is_active)
		self._settings.set_string('style', uri)
		self._backend.update_pandoc_combobox()

	############################################################################
	# Backend management #######################################################

	def set_command_for_format(self, output_format):
		if output_format == 'custom':
			command = self._settings.get_string('custom-render')
			self._backend.set_pandoc_command(command)
			return

		command = 'pandoc $INPUT_FILE %s'
		options = '--metadata pagetitle=Preview'
		accept_css = True

		if self.css_manager.switch_css.get_state() and accept_css:
			options = options + ' -c ' + self.css_manager.css_uri
		self._backend.set_pandoc_command(command % options)

	############################################################################
################################################################################

