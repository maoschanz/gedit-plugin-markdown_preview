# __init__.py
# GPL v3

import subprocess, gi, os
from gi.repository import Gtk

BACKEND_P3MD_AVAILABLE = True
BACKEND_PANDOC_AVAILABLE = True
try:
	import markdown
except Exception:
	print("Package python3-markdown not installed")
	BACKEND_P3MD_AVAILABLE = False

try:
	subprocess.call(['which', 'pandoc'])
except Exception:
	print("Package pandoc not installed")
	BACKEND_PANDOC_AVAILABLE = False

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	import gettext
	gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
	gettext.textdomain('gedit-plugin-markdown-preview')
	_ = gettext.gettext
except:
	_ = lambda s: s

P3MD_PLUGINS = ['admonition', 'codehilite', 'extra', 'nl2br', 'sane_lists', \
                                                   'smarty', 'toc', 'wikilinks']

class MdExportDialog(Gtk.Dialog):
	__gtype_name__ = 'MdExportDialog'

	file_format = 'md'
	output_extension = '.pdf'

	def __init__(self, file_format, gedit_window, settings, **kwargs):
		super().__init__(use_header_bar=True, title=_("Export as…"), **kwargs)
		self.file_format = file_format
		self.gedit_window = gedit_window
		self._settings = settings
		self.plugins = {}
		self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
		self.add_button(_("Next"), Gtk.ResponseType.OK)

		if not BACKEND_P3MD_AVAILABLE and not BACKEND_PANDOC_AVAILABLE:
			error_label = Gtk.Label(label=_("Error: please install pandoc or python3-markdown"))
			self.get_content_area().add(error_label)
			return

		builder = Gtk.Builder().new_from_file(BASE_PATH + '/backend_box.ui')
		self.get_content_area().add(builder.get_object('backend_box'))
		self.export_stack = builder.get_object('backend_stack')
		self.export_stack.show_all() # XXX

		if not BACKEND_P3MD_AVAILABLE:
			self.export_stack.set_visible_child_name('backend_pandoc')
			builder.get_object('switcher_box').set_visible(False)
		elif not BACKEND_PANDOC_AVAILABLE:
			self.export_stack.set_visible_child_name('backend_python')
			builder.get_object('switcher_box').set_visible(False)
		else:
			active_backend = self._settings.get_string('backend')
			self.export_stack.set_visible_child_name('backend_' + active_backend)

		# Load UI for the python3-markdown backend
		for plugin_id in P3MD_PLUGINS:
			self.plugins[plugin_id] = builder.get_object('plugins_' + plugin_id)
		self.load_plugins_list()
		self.get_content_area().add(Gtk.Separator(visible=True))

		# Using a stylesheet is possible with both backends
		builder2 = Gtk.Builder().new_from_file(BASE_PATH + '/css_box.ui')
		css_box = builder2.get_object('css_box')
		css_box.set_margin_left(20)
		css_box.set_margin_right(20)
		css_box.set_margin_top(20)
		css_box.set_margin_bottom(20)
		self.get_content_area().add(css_box)
		self.switch_css = builder2.get_object('switch_css')
		self.switch_css.connect('notify::active', self.on_css_changed)
		self.css_sensitive_box = builder2.get_object('css_sensitive_box')
		self.css_path = self._settings.get_string('style')
		self.file_chooser_btn_css = builder2.get_object('file_chooser_btn_css')
		self.file_chooser_btn_css.set_label('…' + self.css_path[-50:])

		# Load UI for the pandoc backend
		self.pandoc_cli_entry = builder.get_object('pandoc_command_entry')
		self.remember_button = builder.get_object('remember_button')
		self.remember_button.connect('clicked', self.on_remember)
		self.format_combobox = builder.get_object('format_combobox')
		self.fill_combobox()

	def fill_combobox(self):
		self.format_combobox.append('beamer', _("LaTeX beamer slide show (.tex)"))
		self.format_combobox.append('docx', _("Microsoft Word (.docx)"))
		self.format_combobox.append('html5', _("HTML5"))
		self.format_combobox.append('html_custom', _("HTML5 (with custom CSS)"))
		self.format_combobox.append('latex', _("LaTeX (.tex)"))
		self.format_combobox.append('odt', _("OpenOffice text document (.odt)"))
		self.format_combobox.append('pdf', _("Portable Document Format (.pdf)"))
		self.format_combobox.append('plain', _("plain text (.txt)"))
		self.format_combobox.append('pptx', _("PowerPoint slide show (.pptx)"))
		self.format_combobox.append('rtf', _("Rich Text Format (.rtf)"))
		self.format_combobox.append('revealjs', _("reveal.js (HTML with Javascript)"))
		self.format_combobox.append('custom', _("Custom command line"))
		self.format_combobox.connect('changed', self.on_pandoc_format_changed)
		self.format_combobox.set_active_id('pdf')

	def do_cancel_export(self):
		self.destroy()

	def load_plugins_list(self, *args):
		array = self._settings.get_strv('extensions')
		for plugin_id in array:
			self.plugins[plugin_id].set_active(True)

	def on_css_changed(self, w, a):
		self.css_sensitive_box.set_sensitive(w.get_state())

	def on_remember(self, b):
		self._settings.set_string('custom-export', self.pandoc_command_entry.get_text())

	def on_pandoc_format_changed(self, w):
		output_format = w.get_active_id()

		self.remember_button.set_visible(output_format == 'custom')
		if output_format == 'custom':
			command = self._settings.get_string('custom-export')
			self.pandoc_cli_entry.set_text(command)
			self.output_extension = '.pdf'
			return

		command = 'pandoc $INPUT_FILE %s -o $OUTPUT_FILE'
		options = ''
		if output_format == 'pdf':
			options = '-V geometry=right=2cm -V geometry=left=2cm -V ' \
			                          'geometry=bottom=2cm -V geometry=top=2cm'
			self.output_extension = '.pdf'
		elif output_format == 'revealjs':
			options = '-t revealjs -s -V revealjs-url=http://lab.hakim.se/reveal-js'
			self.output_extension = '.html'
		elif output_format == 'html_custom':
			options = '-t html5 -s -c ' + self._settings.get_string('style')
			self.output_extension = '.html'
		else:
			options = '-t ' + output_format
			if output_format == 'beamer' or output_format == 'latex':
				self.output_extension = '.tex'
			elif output_format == 'html5':
				self.output_extension = '.html'
			elif output_format == 'plain':
				self.output_extension = '.txt'
			else:
				self.output_extension = '.' + output_format
		self.pandoc_cli_entry.set_text(command % options)

	############################################################################

	def do_next(self):
		if self.export_stack.get_visible_child_name() == 'backend_python':
			exported = self.export_python()
		else: # if self.export_stack.get_visible_child_name() == 'backend_pandoc':
			exported = self.export_pandoc()
		# if exported: # XXX doesn't work as expected
		#	self.destroy()
		self.destroy()

	def launch_file_chooser(self, output_extension):
		file_chooser = Gtk.FileChooserNative.new(_("Export the preview"), \
		                        self.gedit_window, Gtk.FileChooserAction.SAVE, \
		                                               _("Export"), _("Cancel"))
		name = self.gedit_window.get_active_document().get_short_name_for_display()
		# TODO retirer l'ancienne extension ?
		name = str(name + ' ' + _("(exported)") + output_extension)
		file_chooser.set_current_name(name)
		response = file_chooser.run()
		if response == Gtk.ResponseType.ACCEPT:
			return file_chooser
		else:
			file_chooser.destroy()
			return None

	def export_python(self):
		file_chooser = self.launch_file_chooser('.html')
		if file_chooser is None:
			return False

		# TODO réellement prendre en compte les plugins
		md_extensions = self._settings.get_strv('extensions') # XXX temporairement

		doc = self.gedit_window.get_active_document()
		start, end = doc.get_bounds()
		unsaved_text = doc.get_text(start, end, True)
		content = markdown.markdown(unsaved_text, extensions=[]) #TODO
		with open(file_chooser.get_filename(), 'w') as f:
			f.write(content)
		if self.switch_css.get_active():
			pre_string = '<html><head><meta charset="utf-8" /><link rel="stylesheet" href="' + \
			            self._settings.get_string('style') + '" /></head><body>'
			post_string = '</body></html>'
			with open(file_chooser.get_filename(), 'r+') as f:
				content = f.read()
				f.seek(0, 0)
				f.write(pre_string.rstrip('\r\n') + '\n' + content)
			with open(file_chooser.get_filename(), 'a') as f:
				f.write(post_string)
		file_chooser.destroy()
		return True

	def export_pandoc(self):
		file_chooser = self.launch_file_chooser(self.output_extension)
		if file_chooser is None:
			return False

		output_format = self.format_combobox.get_active_id()
		doc_path = self.gedit_window.get_active_document().get_location().get_path()
		if output_format == 'pdf':
			subprocess.run(['pandoc', doc_path, \
				'-V', 'geometry=right=2cm',
				'-V', 'geometry=left=2cm',
				'-V', 'geometry=bottom=2cm',
				'-V', 'geometry=top=2cm',
				'-o', file_chooser.get_filename()])
		else:
			cmd = self.pandoc_cli_entry.get_text()
			words = cmd.split()
			words[words.index('$INPUT_FILE')] = doc_path
			words[words.index('$OUTPUT_FILE')] = file_chooser.get_filename()
			subprocess.run(words)
		file_chooser.destroy()
		return True

	############################################################################
################################################################################

