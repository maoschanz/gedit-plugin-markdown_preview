import subprocess
import gi
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, WebKit2, GLib

#isAtBottom = False
isAtBottom = True
relativePaths = True
#relativePaths = False
css_uri = "file:///home/roschan/Bureau/test.css"
#FIXME doivent être options

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
		# This is needed because Python is stupid
		self.temp_file = None
	
	# This is called every time the gui is updated
	def do_update_state(self):
#		if self.window.get_active_view() is not None:
#			self.on_reload(None) # Debug purpose only ? pas aberrant non plus
		pass
		
	def do_activate(self):
		# Defining the action which was set earlier in AppActivatable.
		self._insert_bottom_panel()

	def _insert_bottom_panel(self):
		self.view = WebKit2.WebView()
		
		if isAtBottom:
			self.preview_bar.props.orientation = Gtk.Orientation.HORIZONTAL
		else:
			self.preview_bar.props.orientation = Gtk.Orientation.VERTICAL
		self.preview_bar.pack_start(self.view, expand=True, fill=True, padding=0)
		
		box=Gtk.Box()
		if isAtBottom:
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

		refreshBtn = Gtk.Button()
		refreshBtn.connect("clicked", self.on_reload)
		refreshImage = Gtk.Image()
		refreshImage.set_from_icon_name('view-refresh-symbolic', Gtk.IconSize.BUTTON)
		refreshBtn.add(refreshImage)
		box.pack_end(refreshBtn, expand=False, fill=False, padding=0)
		
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

	def on_reload(self, a):
		# Delete the temp file from the previous document
		if self.temp_file is not None:
			self.temp_file.delete()
		
		# Get the current document
		doc = self.window.get_active_document()
		
		# It will not load documents which are not .md
		name = doc.get_short_name_for_display()
		temp = name.split('.')
		if temp[len(temp)-1] != "md":
			self.view.load_plain_text("This is not a markdown document.")
			return
		
		# Support for relative paths is cool, but breaks CSS in many cases
		if relativePaths:
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
		pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + css_uri + '" /></head><body>'
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
		if isAtBottom:
			panel = self.window.get_bottom_panel()
		else:
			panel = self.window.get_side_panel()
		panel.add_titled(self.preview_bar, 'markdown_preview', "Markdown Preview")
		self.preview_bar.show_all()
#		panel.show()
		panel.set_visible_child(self.preview_bar)
	
	def do_deactivate(self):
		if self.temp_file is not None:
			self.temp_file.delete()
			self.temp_file = None
		self._remove_from_panel()

	def _remove_from_panel(self):
		if isAtBottom:
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
		box=Gtk.Box()
		box.props.orientation = Gtk.Orientation.VERTICAL
		box.props.spacing = 20
		box.props.margin_left = 20
		box.props.margin_right = 20
		box.props.margin_top = 20
		box.props.margin_bottom = 20
		box.props.homogeneous = True
		#--------
		positionSettingBox=Gtk.Box()
		positionSettingBox.props.spacing = 20
		positionSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		positionSettingBox.pack_start(Gtk.Label("Preview position"), expand=False, fill=False, padding=0)
		positionCombobox = Gtk.ComboBoxText()
		positionCombobox.append('side', "Side panel")
		positionCombobox.append('bottom', "Bottom panel")
		positionSettingBox.pack_end(positionCombobox, expand=False, fill=False, padding=0)
		#--------
		relativePathsSettingBox=Gtk.Box()
		relativePathsSettingBox.props.spacing = 20
		relativePathsSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		relativePathsSettingBox.pack_start(Gtk.Label("Use relative paths"), expand=False, fill=False, padding=0)
		relativePathsSettingBox.pack_end(Gtk.Switch(), expand=False, fill=False, padding=0)
		#--------
		styleSettingBox=Gtk.Box()
		styleSettingBox.props.spacing = 20
		styleSettingBox.props.orientation = Gtk.Orientation.HORIZONTAL
		styleSettingBox.pack_start(Gtk.Label("Style"), expand=False, fill=False, padding=0)
		styleCombobox = Gtk.ComboBoxText()
		styleCombobox.append('1', "example1")
		styleCombobox.append('2', "example2")
		styleCombobox.append('3', "example3")
		styleSettingBox.pack_end(styleCombobox, expand=False, fill=False, padding=0)
		#--------
		box.add(positionSettingBox)
		box.add(relativePathsSettingBox)
		box.add(styleSettingBox)
		return box

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


