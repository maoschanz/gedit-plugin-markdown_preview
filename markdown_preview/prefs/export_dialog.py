# export_dialog.py
# GPL v3

import gi, subprocess
from gi.repository import Gtk, Gio

from .rendering_settings import MdCssSettings, MdBackendSettings
from ..utils import get_backends_dict
from ..constants import BackendsEnums

################################################################################

class MdExportDialog(Gtk.Dialog):
	__gtype_name__ = 'MdExportDialog'

	file_format = 'md'
	output_extension = '.pdf'

	def __init__(self, file_format, gedit_window, settings, **kwargs):
		super().__init__(use_header_bar=True, title=_("Export as…"), \
		                        default_width=640, default_height=400, **kwargs)
		self.file_format = file_format
		self.gedit_window = gedit_window
		self._settings = settings

		self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
		self.get_content_area().set_margin_left(20)
		self.get_content_area().set_margin_right(20)
		self.get_content_area().set_margin_top(20)
		self.get_content_area().set_margin_bottom(20)
		self.get_content_area().set_spacing(20)

		AVAILABLE_BACKENDS = get_backends_dict()
		if not AVAILABLE_BACKENDS['p3md'] and not AVAILABLE_BACKENDS['pandoc']:
			error_label = Gtk.Label(visible=True, \
			        label=_("Error: please install pandoc or python3-markdown"))
			self.get_content_area().add(error_label)
			return

		self.add_button(_("Next"), Gtk.ResponseType.OK)

		# Add the backend settings to the dialog
		self._backend = MdBackendSettings(_("Export file with:"), \
		                                            self._settings, False, self)
		self.get_content_area().add(self._backend.full_widget)
		self._backend.fill_pandoc_combobox(BackendsEnums.PandocFormatsFull)

		self.get_content_area().add(Gtk.Separator(visible=True))

		self.no_style_label = Gtk.Label(_("No styling options available for this file format."))
		self.get_content_area().add(self.no_style_label)

		# Using a stylesheet is possible with both backends
		self.css_manager = MdCssSettings(self._settings, self, self)
		self.get_content_area().add(self.css_manager.full_widget)

		self._backend.init_pandoc_combobox('pdf')

	############################################################################

	def update_css(self, is_active, uri):
		self._backend.update_pandoc_combobox()

	def _show_accurate_style_manager(self, show_css, show_revealjs):
		self.css_manager.full_widget.set_visible(show_css)
		self.no_style_label.set_visible(not (show_css or show_revealjs))

	def set_command_for_format(self, output_format):
		if output_format == 'custom':
			command = self._settings.get_string('custom-export')
			self._backend.set_pandoc_command(command)
			self.output_extension = '.pdf' # XXX
			self._show_accurate_style_manager(False, False)
			return

		show_revealjs = False
		show_css = not show_revealjs and output_format != 'plain'
		self._show_accurate_style_manager(show_css, show_revealjs)

		command = 'pandoc $INPUT_FILE %s -o $OUTPUT_FILE'
		options = ''
		accept_css = True
		if output_format == 'pdf':
			options = '-V geometry=right=2cm -V geometry=left=2cm -V ' \
			                 'geometry=bottom=2cm -V geometry=top=2cm'
			self.output_extension = '.pdf'
		else:
			options = '-t ' + output_format
			if output_format == 'beamer' or output_format == 'latex':
				self.output_extension = '.tex'
				# accept_css = False # XXX ?
			elif output_format == 'html5':
				options = options + ' -s'
				self.output_extension = '.html'
			elif output_format == 'plain':
				self.output_extension = '.txt'
				accept_css = False
			else:
				self.output_extension = '.' + output_format
		if self.css_manager.switch_css.get_state() and accept_css:
			options = options + ' -c ' + self.css_manager.css_uri
		self._backend.set_pandoc_command(command % options)

	############################################################################
	# Export process ###########################################################

	def do_next(self):
		if self._backend.get_active_backend() == 'backend_python':
			exported = self.export_p3md()
		else: # if self._backend.get_active_backend() == 'backend_pandoc':
			try:
				exported = self.export_pandoc()
			except Exception as err:
				exported = False
				print(err)
				dialog = Gtk.MessageDialog(self.gedit_window, \
				   Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR, \
				        Gtk.ButtonsType.CLOSE, _("Pandoc encountered an error"))
				dialog.format_secondary_text(str(err))
				dialog.run()
				dialog.destroy()
		return exported

	def launch_file_chooser(self, output_extension):
		file_chooser = Gtk.FileChooserNative.new(_("Export the preview"), \
		                        self.gedit_window, Gtk.FileChooserAction.SAVE, \
		                                               _("Export"), _("Cancel"))
		name = self.gedit_window.get_active_document().get_short_name_for_display()
		# retirer l'ancienne extension ?
		name = str(name + ' ' + _("(exported)") + output_extension)
		file_chooser.set_current_name(name)
		file_chooser.set_do_overwrite_confirmation(True)
		response = file_chooser.run()
		if response == Gtk.ResponseType.ACCEPT:
			return file_chooser
		else:
			file_chooser.destroy()
			return None

	def export_p3md(self):
		file_chooser = self.launch_file_chooser('.html')
		if file_chooser is None:
			return False

		md_extensions = []
		for plugin_id in self._backend.plugins:
			if self._backend.plugins[plugin_id].get_active():
				md_extensions.append(plugin_id)

		doc = self.gedit_window.get_active_document()
		start, end = doc.get_bounds()
		unsaved_text = doc.get_text(start, end, True)
		content = markdown.markdown(unsaved_text, extensions=md_extensions)
		if self.css_manager.is_active():
			pre_string = '<html><head><meta charset="utf-8" />' + \
			      '<link rel="stylesheet" href="' + self.css_manager.css_uri + \
			                                                 '" /></head><body>'
			post_string = '</body></html>'
			content = pre_string + content + post_string

		# TODO the p3md export should propose "pdf" and print to the asked file
		with open(file_chooser.get_filename(), 'w') as f:
			f.write(content)
		file_chooser.destroy()
		return True

	def export_pandoc(self):
		file_chooser = self.launch_file_chooser(self.output_extension)
		if file_chooser is None:
			return False

		output_format = self._backend.format_combobox.get_active_id()
		doc_path = self.gedit_window.get_active_document().get_file().get_location().get_path()
		buff = self._backend.pandoc_cli_entry.get_buffer()
		cmd = buff.get_text(buff.get_start_iter(), buff.get_end_iter(), False)
		words = cmd.split()
		words[words.index('$INPUT_FILE')] = doc_path
		words[words.index('$OUTPUT_FILE')] = file_chooser.get_filename()
		file_chooser.destroy()
		result = subprocess.run(words, capture_output=True)
		if result.stderr:
			raise Exception(result.stderr.decode('utf-8'))
		return True

	############################################################################
################################################################################

