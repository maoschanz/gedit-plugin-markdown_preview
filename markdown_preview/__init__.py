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
	
MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'
BASE_TEMP_NAME = '/tmp/gedit_plugin_markdown_preview'

class MarkdownGeditPluginApp(GObject.Object, Gedit.AppActivatable):
	__gtype_name__ = 'MarkdownGeditPluginApp'
	app = GObject.property(type=Gedit.App)
	
	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		self._build_menu()

	def do_deactivate(self):
		self._remove_menu()
	
	def _build_menu(self):
		self.menu_ext = self.extend_menu('file-section-1')
		menu = Gio.Menu()
		sub_menu_item2 = Gio.MenuItem.new(_("Export the preview"), 'win.export_doc')
		sub_menu_item3 = Gio.MenuItem.new(_("Print the preview"), 'win.print_doc')
		menu.append_item(sub_menu_item2)
		menu.append_item(sub_menu_item3)
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
		# This is the attachment we will make to bottom panel.
		self.preview_bar = Gtk.Box()
		# This is needed because Python is stupid # FIXME dans le activate ?
		self._auto_reload = False
	
	# This is called every time the gui is updated
	def do_update_state(self):
		if self.window.get_active_view() is not None:
			if self.test_if_md():
				self.panel.show()
			if self._auto_reload:
				self.on_reload(None, None)
		
	def do_activate(self):
		# Defining the action which was set earlier in AppActivatable.
		self._connect_menu()
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self._isAtBottom = (self._settings.get_string('position') == 'bottom')
		self._useRelativePaths = self._settings.get_boolean('relative')
		self._settings.connect('changed::position', self.change_panel)
		self.insert_in_adequate_panel()
		self.window.connect('active-tab-changed', self.on_reload)
		self.window.lookup_action('export_doc').set_enabled(False)
		self.window.lookup_action('print_doc').set_enabled(False)
		self.temp_file_html = Gio.File.new_for_path(BASE_TEMP_NAME + '.html')
		self.temp_file_md = Gio.File.new_for_path(BASE_TEMP_NAME + '.md')

	def _connect_menu(self):
		action2 = Gio.SimpleAction(name='export_doc')
		action3 = Gio.SimpleAction(name='print_doc')
		action2.connect('activate', self.export_doc)
		action3.connect('activate', self.print_doc)
		self.window.add_action(action2)
		self.window.add_action(action3)
		
	def insert_in_adequate_panel(self):
		self._webview = WebKit2.WebView() # FIXME optimisable, ralentit tout le merdier
		
		if self._isAtBottom:
			self.preview_bar.props.orientation = Gtk.Orientation.HORIZONTAL
		else:
			self.preview_bar.props.orientation = Gtk.Orientation.VERTICAL
		self.preview_bar.pack_start(self._webview, expand=True, fill=True, padding=0)
		
		box=Gtk.Box()
		if self._isAtBottom:
			box.props.orientation = Gtk.Orientation.VERTICAL
		else:
			box.props.orientation = Gtk.Orientation.HORIZONTAL
		box.props.margin_left = 5
		box.props.margin_right = 5
		box.props.margin_top = 5
		box.props.margin_bottom = 5
		box.props.homogeneous = True
		
		insertBtn = Gtk.Button()
		insertBtn.connect('clicked', self.on_insert)
		insertImage = Gtk.Image()
		insertImage.set_from_icon_name('insert-image-symbolic', Gtk.IconSize.BUTTON)
		insertBtn.add(insertImage)
		box.pack_end(insertBtn, expand=False, fill=False, padding=0)

		self.refreshBtn = Gtk.ToggleButton()
		self.refreshBtn.connect('toggled', self.on_set_reload)
		refreshImage = Gtk.Image()
		refreshImage.set_from_icon_name('view-refresh-symbolic', Gtk.IconSize.BUTTON)
		self.refreshBtn.add(refreshImage)
		box.pack_end(self.refreshBtn, expand=False, fill=False, padding=0)
		
		zoomInBtn = Gtk.Button()
		zoomInBtn.connect('clicked', self.on_zoom_in)
		zoomInImage = Gtk.Image()
		zoomInImage.set_from_icon_name('zoom-in-symbolic', Gtk.IconSize.BUTTON)
		zoomInBtn.add(zoomInImage)
		box.pack_end(zoomInBtn, expand=False, fill=False, padding=0)
		
		zoomOutBtn = Gtk.Button()
		zoomOutBtn.connect('clicked', self.on_zoom_out)
		zoomOutImage = Gtk.Image()
		zoomOutImage.set_from_icon_name('zoom-out-symbolic', Gtk.IconSize.BUTTON)
		zoomOutBtn.add(zoomOutImage)
		box.pack_end(zoomOutBtn, expand=False, fill=False, padding=0)
		
		# box only contains the 4 buttons, it will pack at the end (bottom or right) of
		# the preview_bar object, where the webview has already been added.
		self.preview_bar.pack_end(box, expand=False, fill=False, padding=0)
		
		self.show_on_panel()

	def on_set_reload(self, a):
		if self.refreshBtn.get_active():
			self._auto_reload = True
			self.on_reload(None, None)
		else:
			self._auto_reload = False
	
	def delete_temp_file(self):
		if self.temp_file_html.query_exists():
			self.temp_file_html.delete()
		if self.temp_file_md.query_exists():
			self.temp_file_md.delete()
	
	def test_if_md(self):
		doc = self.window.get_active_document()
		
		# It will not load documents which are not .md
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		if temp[len(temp)-1] != 'md':
			self._webview.load_plain_text(_("This is not a markdown document."))
			self.window.lookup_action('export_doc').set_enabled(False)
			self.window.lookup_action('print_doc').set_enabled(False)
			return False
		else:
			return True
	
	# This needs dummy parameters because it's connected to a signal which give arguments.
	def on_reload(self, osef, oseb):
	
		# Guard clause: it will not load documents which are not .md
		if not self.test_if_md():
			return
		
		dummy_uri = self.get_dummy_uri()

		# Get the current document, or the temporary document if requested
		doc = self.window.get_active_document()
		if self._auto_reload:
			start, end = doc.get_bounds()
			unsaved_text = doc.get_text(start, end, True)
			f = open(BASE_TEMP_NAME + '.md', 'w')
			f.write(unsaved_text)
			f.close()
			file_uri = self.temp_file_md.get_uri()
		else:
			file_uri = doc.get_uri_for_display()
		
		# It uses pandoc to produce the html code
		pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
			self._settings.get_string('style') + '" /></head><body>'
		post_string = '</body></html>'
		result = subprocess.run(['pandoc', file_uri], stdout=subprocess.PIPE)
		html_string = result.stdout.decode('utf-8')
		html_content = pre_string + html_string + post_string
		
		if self._useRelativePaths:
			self._webview.load_html(html_content, dummy_uri)
		else:
			f = open(BASE_TEMP_NAME + '.html', 'w')
			f.write(html_content)
			f.close()
			self._webview.load_uri(self.temp_file_html.get_uri())
		self.window.lookup_action('export_doc').set_enabled(True)
		self.window.lookup_action('print_doc').set_enabled(True)
	
	def get_dummy_uri(self):
		# Support for relative paths is cool, but breaks CSS in many cases
		if self._useRelativePaths:
			return self.window.get_active_document().get_uri_for_display()
		else:
			return None
	
	def show_on_panel(self):
		# Get the bottom bar (A Gtk.Stack), or the side bar, and add our bar to it.
		if self._isAtBottom:
			self.panel = self.window.get_bottom_panel()
		else:
			self.panel = self.window.get_side_panel()
		self.panel.add_titled(self.preview_bar, 'markdown_preview', _("Markdown Preview"))
		self.preview_bar.show_all()
		self.panel.set_visible_child(self.preview_bar)
	
	def do_deactivate(self):
		self.delete_temp_file()
		self._remove_from_panel()

	def _remove_from_panel(self):
		self.panel.remove(self.preview_bar)
	
	def on_zoom_in(self, a):
		if self._webview.get_zoom_level() < 10:
			self._webview.set_zoom_level(self._webview.get_zoom_level() + 0.1)
		
	def on_zoom_out(self, a):
		if self._webview.get_zoom_level() > 0.15:
			self._webview.set_zoom_level(self._webview.get_zoom_level() - 0.1)
		
	def on_insert(self, a):
		doc = self.window.get_active_document()
		
		# It will not insert image if the document is not .md
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		if temp[len(temp)-1] != 'md':
			self._webview.load_plain_text(_("This is not a markdown document."))
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
			picture_path = '![](' + file_chooser.get_filename() + ')'
			iter = doc.get_iter_at_mark(doc.get_insert())
			doc.insert(iter, picture_path)
		file_chooser.destroy()
	
	def change_panel(self, a, b):
		self._remove_from_panel()
		self.preview_bar = Gtk.Box()
		self._isAtBottom = (self._settings.get_string('position') == 'bottom')
		self.insert_in_adequate_panel()
	
	def do_create_configure_widget(self):
		# Just return your box, PeasGtk will automatically pack it into a box and show it.
		widget = MdConfigWidget(self.plugin_info.get_data_dir())
		return widget.get_box()

	def export_doc(self, a, b):
		file_chooser = Gtk.FileChooserDialog(_("Export the preview"), self.window,
			Gtk.FileChooserAction.SAVE,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
		response = file_chooser.run()
		
		# It gets the chosen file's path
		if response == Gtk.ResponseType.OK:
			subprocess.run(['pandoc', self.window.get_active_document().get_location().get_path(), '-o', file_chooser.get_filename()])
		file_chooser.destroy()
		
	def print_doc(self, a, b):
		p = WebKit2.PrintOperation.new(self._webview)
		p.run_dialog()

class MdConfigWidget:

	def __init__(self, datadir):
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self._settings.get_string('position')
		self._settings.get_boolean('relative')
		self._settings.get_string('style')
		
		self.box = Gtk.Box()
		self.box.props.orientation = Gtk.Orientation.VERTICAL
		self.box.props.spacing = 20
		self.box.props.margin_left = 20
		self.box.props.margin_right = 20
		self.box.props.margin_top = 20
		self.box.props.margin_bottom = 20
		self.box.props.homogeneous = True
		#--------
		positionSettingBox=Gtk.Box()
		positionSettingBox.props.spacing = 20
		positionSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		positionSettingBox.pack_start(Gtk.Label(_("Preview position")), expand=False, fill=False, padding=0)
		positionCombobox = Gtk.ComboBoxText()
		positionCombobox.append('side', _("Side panel"))
		positionCombobox.append('bottom', _("Bottom panel"))
		positionCombobox.set_active_id(self._settings.get_string('position'))
		positionCombobox.connect('changed', self.on_position_changed)
		positionSettingBox.pack_end(positionCombobox, expand=False, fill=False, padding=0)
		#--------
		relativePathsSettingBox=Gtk.Box()
		relativePathsSettingBox.props.spacing = 20
		relativePathsSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		relativePathsSettingBox.pack_start(Gtk.Label(_("Use relative paths")), expand=False, fill=False, padding=0)
		relativePathsSwitch = Gtk.Switch()
		relativePathsSwitch.set_state(self._settings.get_boolean('relative'))
		relativePathsSwitch.connect('notify::active', self.on_relative_changed)
		relativePathsSettingBox.pack_end(relativePathsSwitch, expand=False, fill=False, padding=0)
		#--------
		styleSettingBox=Gtk.Box()
		styleSettingBox.props.spacing = 20
		styleSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		styleSettingBox.pack_start(Gtk.Label(_("Stylesheet")), expand=False, fill=False, padding=0)
		self.styleLabel = Gtk.Label(self._settings.get_string('style'))
		styleButton = Gtk.Button()
		styleButton.connect('clicked', self.on_choose_css)
		styleImage = Gtk.Image()
		styleImage.set_from_icon_name('document-open-symbolic', Gtk.IconSize.BUTTON)
		styleButton.add(styleImage)
		styleSettingBox.pack_end(styleButton, expand=False, fill=False, padding=0)
		styleSettingBox.pack_end(self.styleLabel, expand=False, fill=False, padding=0)
		#--------
		self.box.add(positionSettingBox)
		self.box.add(relativePathsSettingBox)
		self.box.add(styleSettingBox)
	
	def get_box(self):
		return self.box
		
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
			self.styleLabel.label = file_chooser.get_uri()
			self._settings.set_string('style', file_chooser.get_uri())
		file_chooser.destroy()
		
	def on_relative_changed(self, w, a):
		if w.get_state():
			self._settings.set_boolean('relative', True)
		else:
			self._settings.set_boolean('relative', False)
	
	
