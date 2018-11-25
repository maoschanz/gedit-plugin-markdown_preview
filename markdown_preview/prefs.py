import subprocess
import gi
import os
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, WebKit2, GLib

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'
BASE_TEMP_NAME = '/tmp/gedit_plugin_markdown_preview'

try:
    import gettext
    gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
    gettext.textdomain('gedit-plugin-markdown-preview')
    _ = gettext.gettext
except:
    _ = lambda s: s
    
class MdConfigWidget(Gtk.Box):
	__gtype_name__ = 'MdConfigWidget'

	def __init__(self, datadir, **kwargs):
		super().__init__(**kwargs, orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=10)
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		#--------
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'prefs.ui'))
#		builder.set_translation_domain('gedit-plugin-markdown-preview') # ?????? FIXME
		stack = Gtk.Stack(margin=10)
		switcher = Gtk.StackSwitcher(stack=stack, halign=Gtk.Align.CENTER)
		
		preview_page = builder.get_object('preview_page')
		shortcuts_page = builder.get_object('shortcuts_page')
		
		stack.add_titled(preview_page, 'preview', _("Preview"))
		stack.add_titled(shortcuts_page, 'shortcuts', _("Shortcuts"))
		
		### PREVIEW ###
		
		backendCombobox = builder.get_object('backendCombobox')
		backendCombobox.append('python', _("python3-markdown"))
		backendCombobox.append('pandoc', _("pandoc"))
		backendCombobox.set_active_id(self._settings.get_string('backend'))
		backendCombobox.connect('changed', self.on_backend_changed)
		
		self.pandocCommandBox = builder.get_object('pandocCommandBox')
		self.python3MarkdownPluginsBox = builder.get_object('python3MarkdownPluginsBox')
		
		self.pandocCommandEntry = builder.get_object('pandocCommandEntry')
		
		self.plugins_extra = builder.get_object('plugins_extra')
		self.plugins_toc = builder.get_object('plugins_toc')
		self.plugins_smarty = builder.get_object('plugins_smarty')
		self.plugins_codehilite = builder.get_object('plugins_codehilite')
		self.plugins_nl2br = builder.get_object('plugins_nl2br')
		self.plugins_sanelists = builder.get_object('plugins_sanelists')
		self.plugins_admonition = builder.get_object('plugins_admonition')
		self.plugins_wikilinks = builder.get_object('plugins_wikilinks')
		
		self.load_plugins_list()
		
		self.plugins_extra.connect('clicked', self.update_plugins_list)
		self.plugins_toc.connect('clicked', self.update_plugins_list)
		self.plugins_smarty.connect('clicked', self.update_plugins_list)
		self.plugins_codehilite.connect('clicked', self.update_plugins_list)
		self.plugins_nl2br.connect('clicked', self.update_plugins_list)
		self.plugins_sanelists.connect('clicked', self.update_plugins_list)
		self.plugins_admonition.connect('clicked', self.update_plugins_list)
		self.plugins_wikilinks.connect('clicked', self.update_plugins_list)
		
		#--------
		relativePathsSwitch = builder.get_object('relativePathsSwitch')
		relativePathsSwitch.set_state(self._settings.get_boolean('relative'))
		relativePathsSwitch.connect('notify::active', self.on_relative_changed)
		#--------
		autoManageSwitch = builder.get_object('autoManageSwitch')
		autoManageSwitch.set_state(self._settings.get_boolean('auto-manage-panel'))
		autoManageSwitch.connect('notify::active', self.on_auto_manage_changed)
		#--------
		self.styleLabel = builder.get_object('styleLabel')
		if len(self._settings.get_string('style')) >= 42:
			self.styleLabel.set_label("…" + self._settings.get_string('style')[-40:])
		else:
			self.styleLabel.set_label(self._settings.get_string('style'))
#		self.styleLabel = Gtk.Label(self._settings.get_string('style'))
		styleButton = builder.get_object('styleButton')
		styleButton.connect('clicked', self.on_choose_css)
		
		### SHORTCUTS ###
#		TODO
		shortcuts_box = builder.get_object('shortcuts_box')
		shortcuts_box.add(MdKeybindingWidget("test 1"))
		shortcuts_box.add(MdKeybindingWidget("test 2"))
		
#		https://github.com/GNOME/gtk/blob/master/gdk/keynames.txt
		
		
		self.add(switcher)
		self.add(stack)
		
		self.connect('notify::visible', self.set_options_visibility)
	
	def on_backend_changed(self, w):
		self._settings.set_string('backend', w.get_active_id())
		self.set_options_visibility()
		
	def update_plugins_list(self, *args):
		array = []
		if self.plugins_admonition.get_active():
			array.append('admonition')
		if self.plugins_codehilite.get_active():
			array.append('codehilite')
		if self.plugins_extra.get_active():
			array.append('extra')
		if self.plugins_nl2br.get_active():
			array.append('nl2br')
		if self.plugins_sanelists.get_active():
			array.append('sane_lists')
		if self.plugins_smarty.get_active():
			array.append('smarty')
		if self.plugins_toc.get_active():
			array.append('toc')
		if self.plugins_wikilinks.get_active():
			array.append('wikilinks')
		self._settings.set_strv('extensions', array)
			
	def load_plugins_list(self, *args):
		array = self._settings.get_strv('extensions')
		if array.count('admonition') != 0:
			self.plugins_admonition.set_active(True)
		if array.count('codehilite') != 0:
			self.plugins_codehilite.set_active(True)
		if array.count('extra') != 0:
			self.plugins_extra.set_active(True)
		if array.count('nl2br') != 0:
			self.plugins_nl2br.set_active(True)
		if array.count('sane_lists') != 0:
			self.plugins_sanelists.set_active(True)
		if array.count('smarty') != 0:
			self.plugins_smarty.set_active(True)
		if array.count('toc') != 0:
			self.plugins_toc.set_active(True)
		if array.count('wikilinks') != 0:
			self.plugins_wikilinks.set_active(True)
		
	def set_options_visibility(self, *args):
		backend = self._settings.get_string('backend')
		if backend == 'pandoc':
			self.python3MarkdownPluginsBox.set_visible(False)
			self.pandocCommandBox.set_visible(True)
		else:
			self.pandocCommandBox.set_visible(False)
			self.python3MarkdownPluginsBox.set_visible(True)
		
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
		if w.get_state():
			self._settings.set_boolean('relative', True)
		else:
			self._settings.set_boolean('relative', False)
		
	def on_auto_manage_changed(self, w, a):
		if w.get_state():
			self._settings.set_boolean('auto-manage-panel', True)
		else:
			self._settings.set_boolean('auto-manage-panel', False)
	
##################################################

class MdKeybindingWidget(Gtk.ListBoxRow):
	__gtype_name__ = "MdKeybindingWidget"
	
	def __init__(self, description, **kwargs):
		super().__init__(can_focus=True, activatable=False, selectable=False)
		row_box = Gtk.Box(spacing=12, orientation=Gtk.Orientation.HORIZONTAL)
		self.add(row_box)
		
		description = Gtk.Label(label=description)
		row_box.pack_start(description, expand=True, fill=True, padding=0)
		
		self.treeView = Gtk.TreeView(
			enable_grid_lines=True,
			headers_visible=False
		)
		self.accelCell = Gtk.CellRendererAccel(
			accel_mode=Gtk.CellRendererAccelMode.GTK,
			editable=True
		)
		accelCol = Gtk.TreeViewColumn();
		accelCol.pack_end(self.accelCell, False);
		accelCol.add_attribute(self.accelCell, "accel-key", 2);
		accelCol.add_attribute(self.accelCell, "accel-mods", 3);
		self.treeView.append_column(accelCol);
		
		row_box.pack_start(self.treeView, expand=True, fill=True, padding=0)
		
		
		
		self.accelCell.connect("accel-edited", self.accel_edited_cb)
		
		
		self.show_all()
		
	def accel_edited_cb(self, *args):
		print(args) # FIXME non ne marche pas
		
		

