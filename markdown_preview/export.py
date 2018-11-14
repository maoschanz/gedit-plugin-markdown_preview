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
		
		self.plugins_extra = builder.get_object('plugins_extra')
		self.plugins_toc = builder.get_object('plugins_toc')
		self.plugins_smarty = builder.get_object('plugins_smarty')
		self.plugins_codehilite = builder.get_object('plugins_codehilite')
		self.plugins_nl2br = builder.get_object('plugins_nl2br')
		self.plugins_sanelists = builder.get_object('plugins_sanelists')
		self.plugins_admonition = builder.get_object('plugins_admonition')
		self.plugins_wikilinks = builder.get_object('plugins_wikilinks')
		
		self.load_plugins_list()
		
		self.switch_css = builder.get_object('switch_css')
		self.switch_css.connect('notify::active', self.on_css_changed)
		self.css_box = builder.get_object('css_box')
		self.css_path = self._settings.get_string('style')
		self.file_chooser_btn_css = builder.get_object('file_chooser_btn_css')
		self.file_chooser_btn_css.set_label('…' + self.css_path[-50:])
		
		self.pandoc_command_entry = builder.get_object('pandoc_command_entry')
		self.remember_button = builder.get_object('remember_button')
		self.remember_button.connect('clicked', self.on_remember)
		
		self.format_combobox = builder.get_object('format_combobox')
		self.format_combobox.append('beamer', _("LaTeX beamer slide show"))
		self.format_combobox.append('docx', _("Microsoft Word (.docx)"))
		self.format_combobox.append('html5', _("HTML5"))
		self.format_combobox.append('html_custom', _("HTML5 (with custom CSS)"))
		self.format_combobox.append('latex', _("LaTeX (.tex)"))
		self.format_combobox.append('odt', _("OpenOffice text document (.odt)"))
		self.format_combobox.append('pdf', _("Portable Document Format (.pdf)"))
		self.format_combobox.append('plain', _("plain text"))
		self.format_combobox.append('pptx', _("PowerPoint slide show"))
		self.format_combobox.append('rtf', _("Rich Text Format (.rtf)"))
		self.format_combobox.append('revealjs', _("reveal.js HTML + Javascript slide show"))
		self.format_combobox.append('custom', _("Custom command line"))
		self.format_combobox.connect('changed', self.on_pandoc_format_changed)
		self.format_combobox.set_active_id('pdf')
		
	def do_cancel_export(self):
		self.destroy()
		
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
		
	def export_python(self):
		file_chooser = self.launch_file_chooser()
		if file_chooser is None:
			return
			
		# TODO les plugins
		md_extensions = self._settings.get_strv('extensions') # XXX temporairement
		
		doc = self.gedit_window.get_active_document()
		start, end = doc.get_bounds()
		unsaved_text = doc.get_text(start, end, True)
		content = markdown.markdown(unsaved_text, extensions=[]) #TODO
		with open(file_chooser.get_filename(), 'w') as f:
			f.write(content)
			f.close()
		if self.switch_css.get_active():
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
		file_chooser.destroy()

	def export_pandoc(self):
		file_chooser = self.launch_file_chooser()
		if file_chooser is None:
			return
		output_format = self.format_combobox.get_active_id()
		if output_format == 'pdf':
			subprocess.run(['pandoc', self.gedit_window.get_active_document().get_location().get_path(), \
				'-V', 'geometry=right=2cm',
				'-V', 'geometry=left=2cm',
				'-V', 'geometry=bottom=2cm',
				'-V', 'geometry=top=2cm',
				'-o', file_chooser.get_filename()])
		else:
			cmd = self.pandoc_command_entry.get_text()
			words = cmd.split()
			words[words.index('$INPUT_FILE')] = self.gedit_window.get_active_document().get_location().get_path()
			words[words.index('$OUTPUT_FILE')] = file_chooser.get_filename()
			subprocess.run(words)
		file_chooser.destroy()

	def launch_file_chooser(self):
		file_chooser = Gtk.FileChooserDialog(_("Export the preview"), self.gedit_window,
			Gtk.FileChooserAction.SAVE,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
		response = file_chooser.run()
		if response == Gtk.ResponseType.OK:
			return file_chooser
		else:
			file_chooser.destroy()
			return None

	def do_next(self):
		if self.export_stack.get_visible_child_name() == 'export_python':
			self.export_python()
		elif self.export_stack.get_visible_child_name() == 'export_pandoc':
			self.export_pandoc()
		self.destroy()

	def on_css_changed(self, w, a):
		self.css_box.set_visible(w.get_state())

	def on_remember(self, b):
		self._settings.set_string('custom-export', self.pandoc_command_entry.get_text())

	def on_pandoc_format_changed(self, w):
		output_format = w.get_active_id()
		self.remember_button.set_visible(output_format == 'custom')
		
		if output_format == 'pdf':
			self.pandoc_command_entry.set_text('pandoc $INPUT_FILE -V geometry=right=2cm -V' \
				' geometry=left=2cm -V geometry=bottom=2cm -V geometry=top=2cm -o $OUTPUT_FILE')
		elif output_format == 'revealjs':
			self.pandoc_command_entry.set_text('pandoc $INPUT_FILE -t revealjs -s -V revealjs-url=http://lab.hakim.se/reveal-js -o $OUTPUT_FILE')
		elif output_format == 'custom':
			self.pandoc_command_entry.set_text(self._settings.get_string('custom-export'))
		elif output_format == 'html_custom':
			self.pandoc_command_entry.set_text('pandoc $INPUT_FILE -t html5 -s -c ' + self._settings.get_string('style') + ' -o $OUTPUT_FILE')
		else:
			self.pandoc_command_entry.set_text('pandoc $INPUT_FILE -t ' + output_format + ' -o $OUTPUT_FILE')

#################

