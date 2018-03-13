import subprocess
import gi
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, WebKit2, GLib

MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'

class MarkdownGeditPluginApp(GObject.Object, Gedit.AppActivatable):
	__gtype_name__ = "MarkdownGeditPluginApp"
	app = GObject.property(type=Gedit.App)
	
	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		pass

	def do_deactivate(self):
		pass

class MarkdownGeditPluginWindow(GObject.Object, Gedit.WindowActivatable, PeasGtk.Configurable):
	window = GObject.property(type=Gedit.Window)
	__gtype_name__ = "MarkdownGeditPluginWindow"

	def __init__(self):
		GObject.Object.__init__(self)
		# This is the attachment we will make to bottom panel.
		self.preview_bar = Gtk.Box()
		# This is needed because Python is stupid # FIXME dans le activate ?
		self.temp_file = None
		self._auto_reload = False
	
	# This is called every time the gui is updated
	def do_update_state(self):
		if self.window.get_active_view() is not None:
			if self._auto_reload:
				self.on_reload()
			if self.test_if_md():
				self.panel.show()
		
	def do_activate(self):
		# Defining the action which was set earlier in AppActivatable.
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		self._isAtBottom = (self._settings.get_string('position') == 'bottom')
		self._useRelativePaths = self._settings.get_boolean('relative')
		self.insert_in_adequate_panel()

	def insert_in_adequate_panel(self):
		self.view = WebKit2.WebView() # FIXME optimisable, ralentit tout le merdier
		
		if self._isAtBottom:
			self.preview_bar.props.orientation = Gtk.Orientation.HORIZONTAL
		else:
			self.preview_bar.props.orientation = Gtk.Orientation.VERTICAL
		self.preview_bar.pack_start(self.view, expand=True, fill=True, padding=0)
		
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
		insertBtn.connect("clicked", self.on_insert)
		insertImage = Gtk.Image()
		insertImage.set_from_icon_name('insert-image-symbolic', Gtk.IconSize.BUTTON)
		insertBtn.add(insertImage)
		box.pack_end(insertBtn, expand=False, fill=False, padding=0)

		self.refreshBtn = Gtk.ToggleButton()
		self.refreshBtn.connect("toggled", self.on_set_reload)
		refreshImage = Gtk.Image()
		refreshImage.set_from_icon_name('view-refresh-symbolic', Gtk.IconSize.BUTTON)
		self.refreshBtn.add(refreshImage)
		box.pack_end(self.refreshBtn, expand=False, fill=False, padding=0)
		
		zoomInBtn = Gtk.Button()
		zoomInBtn.connect("clicked", self.on_zoom_in)
		zoomInImage = Gtk.Image()
		zoomInImage.set_from_icon_name('zoom-in-symbolic', Gtk.IconSize.BUTTON)
		zoomInBtn.add(zoomInImage)
		box.pack_end(zoomInBtn, expand=False, fill=False, padding=0)
		
		zoomOutBtn = Gtk.Button()
		zoomOutBtn.connect("clicked", self.on_zoom_out)
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
		else:
			self._auto_reload = False
	
	def delete_temp_file(self):
		# Delete the temp file from the previous document
		if self.temp_file is not None:
			self.temp_file.delete()
			self.temp_file = None
	
	def test_if_md(self):
		doc = self.window.get_active_document()
		
		# It will not load documents which are not .md
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		if temp[len(temp)-1] != "md":
			self.view.load_plain_text("This is not a markdown document.")
			return False
		else:
			return True
		
	def on_reload(self):
		self.delete_temp_file()
	
		# Get the current document
		doc = self.window.get_active_document()
		
		# It will not load documents which are not .md
		if not self.test_if_md():
			return
		
		# Support for relative paths is cool, but breaks CSS in many cases
		if self._useRelativePaths:
			path = doc.get_location()
			arr = path.get_path().split('/')
			del arr[-1]
			parent_path = ''
			for element in arr:
				parent_path = parent_path + '/' + element
		else:
			parent_path = '/tmp'
		
		# It uses pandoc to produce the html code
		uri = doc.get_uri_for_display()
		pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
			self._settings.get_string('style') + '" /></head><body>'
		post_string = '</body></html>'
		result = subprocess.run(['pandoc', uri], stdout=subprocess.PIPE)
		html_string = result.stdout.decode('utf-8')
		content = pre_string + html_string + post_string
#		self.view.load_html(content, uri) #Simpler but doesn't load the CSS file ???
		
		# It sets the html code in a file, and previews the file
		f = open(parent_path + '/gedit_plugin_markdown_preview', 'w') #TODO mettre en caché
		f.write(content)
		self.temp_file = Gio.File.new_for_path(parent_path + '/gedit_plugin_markdown_preview')
		self.view.load_uri(self.temp_file.get_uri())
	
	def show_on_panel(self):
		# Get the bottom bar (A Gtk.Stack), or the side bar, and add our bar to it.
		if self._isAtBottom:
			self.panel = self.window.get_bottom_panel()
		else:
			self.panel = self.window.get_side_panel()
		self.panel.add_titled(self.preview_bar, 'markdown_preview', "Markdown Preview")
		self.preview_bar.show_all()
		self.panel.set_visible_child(self.preview_bar)
	
	def do_deactivate(self):
		if self.temp_file is not None:
			self.temp_file.delete()
			self.temp_file = None
		self._remove_from_panel()

	def _remove_from_panel(self):
		if self._isAtBottom:
			panel = self.window.get_bottom_panel()
		else:
			panel = self.window.get_side_panel()
		panel.remove(self.preview_bar)
	
	def on_zoom_in(self, a):
		if self.view.get_zoom_level() < 10:
			self.view.set_zoom_level(self.view.get_zoom_level() + 0.1)
		
	def on_zoom_out(self, a):
		if self.view.get_zoom_level() > 0.15:
			self.view.set_zoom_level(self.view.get_zoom_level() - 0.1)
		
	def on_insert(self, a):
		doc = self.window.get_active_document()
		
		# It will not insert image if the document is not .md
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		if temp[len(temp)-1] != "md":
			self.view.load_plain_text("This is not a markdown document.")
			return
		
		# Building a FileChooserDialog for pictures
		file_chooser = Gtk.FileChooserDialog("Select a picture", self.window,
			Gtk.FileChooserAction.OPEN,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		onlyPictures = Gtk.FileFilter()
		onlyPictures.set_name("Pictures")
		onlyPictures.add_mime_type("image/*")
		file_chooser.set_filter(onlyPictures)
		response = file_chooser.run()
		
		# It gets the chosen file's path
		if response == Gtk.ResponseType.OK:
			picture_path = '![](' + file_chooser.get_filename() + ')'
		elif response == Gtk.ResponseType.CANCEL:
			picture_path = ''
		file_chooser.destroy()

		# It inserts it at the current position
		iter = doc.get_iter_at_mark(doc.get_insert())
		doc.insert(iter, picture_path)

	def do_create_configure_widget(self):
		# Just return your box, PeasGtk will automatically pack it into a box and show it.
		widget = MdConfigWidget(self.plugin_info.get_data_dir())
		return widget.get_box()

class MdView(WebKit2.WebView):
	"WebKit view"

	def new(window):
		context = WebKit2.WebContext.new()
		webview = WebKit2.WebView.new_with_context(context)
		content_manager = webview.get_property("user-content-manager")
		self._window = window
		self.__context = context
		self.__content_manager = content_manager
		self._uri = None
		self._title = None
		self._navigation_uri = None
		self.set_hexpand(True)
		self.set_vexpand(True)
		Gtk.Overlay.do_get_preferred_width(self)
		Gtk.Overlay.do_get_preferred_height(self)
		return webview

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
		positionSettingBox.pack_start(Gtk.Label("Preview position"), expand=False, fill=False, padding=0)
		positionCombobox = Gtk.ComboBoxText()
		positionCombobox.append('side', "Side panel")
		positionCombobox.append('bottom', "Bottom panel")
		positionCombobox.connect("changed", self.on_position_changed)
		positionCombobox.set_active_id(self._settings.get_string('position'))
		positionSettingBox.pack_end(positionCombobox, expand=False, fill=False, padding=0)
		#--------
		relativePathsSettingBox=Gtk.Box()
		relativePathsSettingBox.props.spacing = 20
		relativePathsSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		relativePathsSettingBox.pack_start(Gtk.Label("Use relative paths"), expand=False, fill=False, padding=0)
		relativePathsSwitch = Gtk.Switch()
		relativePathsSwitch.set_active(self._settings.get_boolean('relative'))
		relativePathsSwitch.connect('notify::active', self.on_relative_changed)
		relativePathsSettingBox.pack_end(relativePathsSwitch, expand=False, fill=False, padding=0)
		#--------
		styleSettingBox=Gtk.Box()
		styleSettingBox.props.spacing = 20
		styleSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		styleSettingBox.pack_start(Gtk.Label("Style"), expand=False, fill=False, padding=0)
		self.styleLabel = Gtk.Label(self._settings.get_string('style'))
		styleButton = Gtk.Button()
		styleButton.connect("clicked", self.on_choose_css)
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
		file_chooser = Gtk.FileChooserDialog("Select a CSS file", None, # FIXME
			Gtk.FileChooserAction.OPEN,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		onlyCSS = Gtk.FileFilter()
		onlyCSS.set_name("Stylesheet")
		onlyCSS.add_mime_type("text/css")
		file_chooser.set_filter(onlyCSS)
		response = file_chooser.run()
		
		# It gets the chosen file's path
		if response == Gtk.ResponseType.OK:
			self.styleLabel.label = file_chooser.get_uri()
			self._settings.set_string('style', file_chooser.get_uri())
		file_chooser.destroy()
		
	def on_relative_changed(self, w, a):
		if w.active:
			self._settings.set_boolean('relative', True);
		else:
			self._settings.set_boolean('relative', False);
	
	
