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
		super().__init__(**kwargs, orientation=Gtk.Orientation.VERTICAL,spacing=10)
		self._settings = Gio.Settings.new(MD_PREVIEW_KEY_BASE)
		#--------
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'prefs.ui'))
#		builder.set_translation_domain('gedit-plugin-markdown-preview') # ?????? FIXME
		stack = Gtk.Stack(margin=20)
		switcher = Gtk.StackSwitcher(stack=stack, halign=Gtk.Align.CENTER)
		
		preview_page = builder.get_object('preview_page')
		export_page = builder.get_object('export_page')
		shortcuts_page = builder.get_object('shortcuts_page')
		
		stack.add_titled(preview_page, 'preview', _("Preview"))
		stack.add_titled(export_page, 'export', _("Export"))
		stack.add_titled(shortcuts_page, 'shortcuts', _("Shortcuts"))
		
		backendCombobox = builder.get_object('backendCombobox')
		backendCombobox.append('python', _("python3-markdown"))
		backendCombobox.append('pandoc', _("pandoc"))
		backendCombobox.set_active_id(self._settings.get_string('backend'))
		backendCombobox.connect('changed', self.on_backend_changed)
		#--------
		positionCombobox = builder.get_object('positionCombobox')
		positionCombobox.append('side', _("Side Panel"))
		positionCombobox.append('bottom', _("Bottom Panel"))
		positionCombobox.set_active_id(self._settings.get_string('position'))
		positionCombobox.connect('changed', self.on_position_changed)
		#--------
		relativePathsSwitch = builder.get_object('relativePathsSwitch')
		relativePathsSwitch.set_state(self._settings.get_boolean('relative'))
		relativePathsSwitch.connect('notify::active', self.on_relative_changed)
		#--------
		pdflatexSwitch = builder.get_object('pdflatexSwitch')
		pdflatexSwitch.set_state(self._settings.get_boolean('pdflatex'))
		pdflatexSwitch.connect('notify::active', self.on_pdflatex_changed)
		#--------
		self.styleLabel = builder.get_object('styleLabel')
		if len(self._settings.get_string('style')) >= 37:
			self.styleLabel.set_label("…" + self._settings.get_string('style')[-35:])
		else:
			self.styleLabel.set_label(self._settings.get_string('style'))
#		self.styleLabel = Gtk.Label(self._settings.get_string('style'))
		styleButton = builder.get_object('styleButton')
		styleButton.connect('clicked', self.on_choose_css)
		# ------------------
				
#		ATTENTON UNE LIGNE D4IOPTINO PAR FORMAT !!!
#		--toc
#		
#		Beamer
#		
#		-V revealjs-url=http://lab.hakim.se/reveal-js ---> HTML
#		
#		-V theme=/*thème beamer*/
#		
#		-V navigation=/*none, frame, vertical, horizontal*/
#		
#		LaTeX
#		
#		-V papersize.....
#		
#		-V fontsize.....
#		
#		-V geometry.......
#		
#		
#		
		
		self.add(switcher)
		self.add(stack)
		
	def on_backend_changed(self, w):
		self._settings.set_string('backend', w.get_active_id())
		
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
			self.styleLabel.label = file_chooser.get_filename()
			self._settings.set_string('style', file_chooser.get_filename())
		file_chooser.destroy()
		
	def on_relative_changed(self, w, a):
		if w.get_state():
			self._settings.set_boolean('relative', True)
		else:
			self._settings.set_boolean('relative', False)
		
	def on_pdflatex_changed(self, w, a):
		if w.get_state():
			self._settings.set_boolean('pdflatex', True)
		else:
			self._settings.set_boolean('pdflatex', False)
	
##################################################
