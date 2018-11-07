import subprocess, gi, os, markdown
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gio, WebKit2, GLib, Gedit

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

class MdExportDialog(Gtk.Dialog):
	__gtype_name__ = 'MdExportDialog'
	
	use_css = False
	use_reveal = False
	use_pandoc = False
	output_format = 'error'
	file_format = 'md'
	
	def __init__(self, file_format, gedit_window, settings, **kwargs):
		super().__init__(use_header_bar=True, title=_("Export as…"), **kwargs)
		self.file_format = file_format
		self.gedit_window = gedit_window
		self._settings = settings
		self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
		self.add_button(_("Next"), Gtk.ResponseType.OK)
		builder = Gtk.Builder().new_from_file(os.path.join(BASE_PATH, 'export.ui'))
		self.get_content_area().add(builder.get_object('content-area'))
		
		self.export_stack = builder.get_object('export_stack')
		
		# HTML page
		self.file_chooser_btn_js = builder.get_object('file_chooser_btn_js')
		self.switch_js = builder.get_object('switch_js')
		self.file_chooser_btn_css = builder.get_object('file_chooser_btn_css')
		self.switch_css = builder.get_object('switch_css')
		self.export_html_radiobtn = builder.get_object('export_html_radiobtn')
		self.export_html_pandoc_radiobtn = builder.get_object('export_html_pandoc_radiobtn')
		
		self.css_path = self._settings.get_string('style')
		self.js_uri = self._settings.get_string('reveal-js')
		self.file_chooser_btn_css.set_label(self.css_path)
		self.file_chooser_btn_js.set_label(self.js_uri)
		
#		# PDF page
#		self. = builder.get_object('')
#		self. = builder.get_object('')
#		
#		# Custom page
#		self. = builder.get_object('')
#		self. = builder.get_object('')
		
	def do_cancel_export(self):
		self.destroy()
		
	def do_next(self):
		if self.export_stack.get_visible_child_name() == 'export_html':
			self.output_format = 'html'
			if self.switch_css.get_active():
				self.use_css = True
			if self.switch_js.get_active():
				self.use_reveal = True
			if self.export_html_pandoc_radiobtn.get_active():
				self.use_pandoc = True
			# TODO les plugins
		elif self.export_stack.get_visible_child_name() == 'export_pdf':
			self.output_format = 'pdf'
		elif self.export_stack.get_visible_child_name() == 'export_custom':
			self.output_format = 'custom'
		
		file_chooser = Gtk.FileChooserDialog(_("Export the preview"), self.gedit_window,
			Gtk.FileChooserAction.SAVE,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
		response = file_chooser.run()
		
		if response == Gtk.ResponseType.OK:
			if self.output_format == 'html':
				if self.use_pandoc:
					if self.use_reveal:
						subprocess.run(['pandoc', self.gedit_window.get_active_document().get_location().get_path(), \
							'-t', 'revealjs', '-s',
							'-V', 'revealjs-url=http://lab.hakim.se/reveal-js',
							'-o', file_chooser.get_filename()])
					else:
						subprocess.run(['pandoc', self.gedit_window.get_active_document().get_location().get_path(), \
							'-t', 'html',
							'-o', file_chooser.get_filename()])
						if self.use_css:
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
					if self.use_reveal:
						pass
					else:
						doc = self.gedit_window.get_active_document()
						start, end = doc.get_bounds()
						unsaved_text = doc.get_text(start, end, True)
						content = markdown.markdown(unsaved_text, extensions=[]) #TODO
						with open(file_chooser.get_filename(), 'w') as f:
							f.write(content)
							f.close()
						
						if self.use_css:
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
		
		
