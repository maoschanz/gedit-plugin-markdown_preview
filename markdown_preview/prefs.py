# prefs.py
# GPL v3

import subprocess, gi, os
from gi.repository import Gtk, Gio

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

from .kb_acc_data import LABELS
from .kb_acc_data import SETTINGS_KEYS

MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'

try:
	import gettext
	gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
	gettext.textdomain('gedit-plugin-markdown-preview')
	_ = gettext.gettext
except:
	_ = lambda s: s

P3MD_PLUGINS = ['admonition', 'codehilite', 'extra', 'nl2br', 'sane_lists', \
                                                   'smarty', 'toc', 'wikilinks']

class MdConfigWidget(Gtk.Box):
	__gtype_name__ = 'MdConfigWidget'

	def __init__(self, datadir, **kwargs):
		super().__init__(**kwargs, orientation=Gtk.Orientation.VERTICAL, \
		                                                  spacing=10, margin=10)
		# XXX c quoi datadir ??
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self.plugins = {}

		builder = Gtk.Builder().new_from_file(BASE_PATH + '/prefs.ui')
#		builder.set_translation_domain('gedit-plugin-markdown-preview') # FIXME
		stack = builder.get_object('stack')
		switcher = Gtk.StackSwitcher(stack=stack, halign=Gtk.Align.CENTER)

		### PREVIEW PAGE #######################################################

		preview_box = builder.get_object('preview_box')

		relativePathsSwitch = builder.get_object('relativePathsSwitch')
		relativePathsSwitch.set_state(self._settings.get_boolean('relative'))
		relativePathsSwitch.connect('notify::active', self.on_relative_changed)

		autoManageSwitch = builder.get_object('autoManageSwitch')
		autoManageSwitch.set_state(self._settings.get_boolean('auto-manage-panel'))
		autoManageSwitch.connect('notify::active', self.on_auto_manage_changed)

		preview_box.add(Gtk.Separator(visible=True))

		builder2 = Gtk.Builder().new_from_file(BASE_PATH + '/css_box.ui')
		css_box = builder2.get_object('css_box')
		preview_box.add(css_box)

		# XXX marges/spacings irréguliers
		# TODO récupérer et connecter le switch
		self.styleLabel = builder2.get_object('styleLabel')
		if self._settings.get_string('style') == '':
			pass
		elif len(self._settings.get_string('style')) >= 42:
			self.styleLabel.set_label("…" + self._settings.get_string('style')[-40:])
		else:
			self.styleLabel.set_label(self._settings.get_string('style'))
		styleButton = builder2.get_object('file_chooser_btn_css')
		styleButton.connect('clicked', self.on_choose_css)

		### BACKEND PAGE #######################################################

		backend_box = builder.get_object('backend_box')

		# TODO remove unavailable backend (if any)
		backendCombobox = builder.get_object('backendCombobox')
		backendCombobox.append('python', "python3-markdown")
		backendCombobox.append('pandoc', "pandoc")
		backendCombobox.set_active_id(self._settings.get_string('backend'))
		backendCombobox.connect('changed', self.on_backend_changed)

		# XXX marges/spacings irréguliers
		builder3 = Gtk.Builder().new_from_file(BASE_PATH + '/backend_box.ui')
		backend_box2 = builder3.get_object('backend_box')
		self.backend_stack = builder3.get_object('backend_stack')
		builder3.get_object('switcher_box').destroy()
		backend_box.add(backend_box2)
		self.backend_stack.show_all() # XXX

		# Load UI for the python3-markdown backend
		for plugin_id in P3MD_PLUGINS:
			self.plugins[plugin_id] = builder3.get_object('plugins_'+plugin_id)
		self.load_plugins_list()
		for plugin_id in P3MD_PLUGINS:
			self.plugins[plugin_id].connect('clicked', self.update_plugins_list)

		# Load UI for the pandoc backend
		self.pandoc_command_entry = builder3.get_object('pandoc_command_entry')
		self.remember_button = builder3.get_object('remember_button')
		self.remember_button.connect('clicked', self.on_remember)

		self.format_combobox = builder3.get_object('format_combobox')
		self.format_combobox.append('html5', _("HTML5"))
		self.format_combobox.append('html_custom', _("HTML5 (with custom CSS)"))
		self.format_combobox.append('revealjs', _("reveal.js slideshow (HTML with Javascript)"))
		self.format_combobox.append('custom', _("Custom command line"))
		self.format_combobox.connect('changed', self.on_pandoc_format_changed)
		self.format_combobox.set_active_id('html_custom') # FIXME

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
		self.connect('notify::visible', self.set_options_visibility)

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

	def on_backend_changed(self, w):
		self._settings.set_string('backend', w.get_active_id())
		self.set_options_visibility()

	def update_plugins_list(self, *args):
		array = []
		for plugin_id in P3MD_PLUGINS:
			if self.plugins[plugin_id].get_active():
				array.append(plugin_id)
		self._settings.set_strv('extensions', array)

	def load_plugins_list(self, *args):
		array = self._settings.get_strv('extensions')
		for plugin_id in array:
			self.plugins[plugin_id].set_active(True)

	def set_options_visibility(self, *args):
		backend = self._settings.get_string('backend')
		self.backend_stack.set_visible_child_name('backend_' + backend)

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
			self._settings.set_string('style', file_chooser.get_uri())
		file_chooser.destroy()

	def on_relative_changed(self, w, a):
		self._settings.set_boolean('relative', w.get_state())

	def on_auto_manage_changed(self, w, a):
		self._settings.set_boolean('auto-manage-panel', w.get_state())

	def on_pandoc_format_changed(self, w):
		output_format = w.get_active_id()
		# TODO

	def on_remember(self, b):
		new_command = self.pandoc_command_entry.get_text()
		self._settings.set_string('custom-export', new_command)

	############################################################################
################################################################################

