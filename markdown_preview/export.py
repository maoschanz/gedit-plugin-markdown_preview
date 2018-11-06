import subprocess, gi, os, markdown
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gio, WebKit2, GLib, Gedit

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

class MdExportDialog(Gtk.Dialog):
	__gtype_name__ = 'MdExportDialog'
	
	def __init__(self, file_format, gedit_window, settings, **kwargs):
		super().__init__(use_header_bar=True, **kwargs)
		self.file_format = file_format
		self.gedit_window = gedit_window
		self._settings = settings
		self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
		self.add_button(_("Next"), Gtk.ResponseType.OK)
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'export.ui'))
		self.get_content_area().add(builder.get_object('content-area'))
		
	def do_cancel_export(self):
		self.destroy()
		
	def do_next(self):
		file_chooser = Gtk.FileChooserDialog(_("Export the preview"), self.gedit_window,
			Gtk.FileChooserAction.SAVE,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
		response = file_chooser.run()
		
		if response == Gtk.ResponseType.OK:
			if (file_chooser.get_filename().split('.')[-1] == 'html'):
#					subprocess.run(['pandoc', self.gedit_window.get_active_document().get_location().get_path(), \
#						'-o', file_chooser.get_filename()])
				subprocess.run(['pandoc', self.gedit_window.get_active_document().get_location().get_path(), \
					'-t', 'revealjs', '-s',
					'-V', 'revealjs-url=http://lab.hakim.se/reveal-js',
					'-o', file_chooser.get_filename()])
					
				pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
					self._settings.get_string('style') + '" /></head><body>'
				post_string = '</body></html>'
				
				with open(file_chooser.get_filename(), 'r+') as f:
					content = f.read()
					f.seek(0, 0)
					f.write(pre_string.rstrip('\r\n') + '\n' + content)
					f.close()
					
				f=open(file_chooser.get_filename(),'a')
				f.write(post_string)
				f.close()
			else:
				subprocess.run(['pandoc', self.gedit_window.get_active_document().get_location().get_path(), \
					'-o', file_chooser.get_filename()])
		file_chooser.destroy()
		self.destroy()
