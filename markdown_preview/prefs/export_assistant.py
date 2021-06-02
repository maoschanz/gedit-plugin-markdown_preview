# export_assistant.py
# GPL v3

import gi, subprocess
from gi.repository import Gtk, Gio

from .rendering_settings import MdCssSettings, MdRevealjsSettings, MdBackendSettings
from ..utils import get_backends_dict
from ..constants import BackendsEnums

################################################################################

class MdExportAssistant(Gtk.Assistant):
	__gtype_name__ = 'MdExportAssistant'

	def __init__(self, file_format, gedit_window, settings, **kwargs):
		super().__init__(use_header_bar=True, title=_("Export as…"), \
		                        default_width=700, default_height=400, **kwargs)
		self.file_format = file_format
		self.gedit_window = gedit_window
		self._settings = settings
		self.output_extension = '.pdf'

		if self._init_1st_page():
			self._init_2nd_page()
			self._init_3rd_page()

	############################################################################

	def _init_1st_page(self):
		format_page = Gtk.Box(visible=True, margin=8, spacing=12, \
		                                   orientation=Gtk.Orientation.VERTICAL)
		available_formats = {}
		self._all_radio_btns = {}

		AVAILABLE_BACKENDS = get_backends_dict()
		if AVAILABLE_BACKENDS['p3md']:
			available_formats = {
				'pdf': _("Portable Document Format (.pdf)"),
				'html5': _("HTML5"),
			}
		if AVAILABLE_BACKENDS['pandoc']:
			available_formats = BackendsEnums.PandocFormatsFull

		if not available_formats:
			error_label = Gtk.Label(visible=True, \
			        label=_("Error: please install pandoc or python3-markdown"))
			self.append_page(error_label)
			self.set_page_type(error_label, Gtk.AssistantPageType.SUMMARY)
			return False

		self._radio_format_group = None
		horizontal_box = Gtk.Box(spacing=12)
		horizontal_box.add(self._get_format_radio(available_formats, 'pdf'))
		horizontal_box.add(self._get_format_radio(available_formats, 'html5'))
		format_page.add(horizontal_box)
		horizontal_box.show_all()

		flowbox = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE)
		if len(available_formats) > 2:
			format_page.add(Gtk.Separator(visible=True))
			format_page.add(Gtk.Label(visible=True, halign=Gtk.Align.START, \
			                                    label=_("Other file formats:")))
			format_page.add(flowbox)

		for file_format in available_formats:
			if file_format in ['pdf', 'html5']:
				continue
			radio = self._get_format_radio(available_formats, file_format, False)
			flowbox.add(radio)
		flowbox.show_all()

		self._add_page(format_page, _("Output file format"), Gtk.AssistantPageType.CONTENT)
		return True

	def _init_2nd_page(self):
		options_page = Gtk.Box(visible=True, margin=12, spacing=8, \
		                                   orientation=Gtk.Orientation.VERTICAL)

		# Add the backend settings to the dialog
		self._backend = MdBackendSettings(_("Export file with:"), \
		                                            self._settings, False, self)
		options_page.add(self._backend.full_widget)
		self._backend.fill_pandoc_combobox(BackendsEnums.PandocFormatsFull)

		options_page.add(Gtk.Separator(visible=True))

		self.no_style_label = Gtk.Label(_("No styling options available for this file format."))
		options_page.add(self.no_style_label)

		# Using a stylesheet is possible with both backends
		self.css_manager = MdCssSettings(self._settings, self, self)
		options_page.add(self.css_manager.full_widget)

		# Shown instead of the CSS manager if user wants to export as revealjs
		self.revealjs_manager = MdRevealjsSettings(self._settings, self)
		options_page.add(self.revealjs_manager.full_widget)

		# It has to be initialized after the CSS module is here
		self._backend.init_pandoc_combobox('pdf')

		self._add_page(options_page, _("Rendering options"), Gtk.AssistantPageType.CONTENT)

	def _init_3rd_page(self):
		wait_spinner = Gtk.Spinner(visible=True)
		wait_spinner.start()
		self._add_page(wait_spinner, _("Export"), Gtk.AssistantPageType.PROGRESS)

	def _add_page(self, page, label, page_type):
		self.append_page(page)
		self.set_page_type(page, page_type)
		self.set_page_complete(page, True)
		self.set_page_title(page, label)

	def _get_format_radio(self, available_formats, file_format, wide=True):
		file_format_label = available_formats[file_format]
		if self._radio_format_group is None:
			radio = Gtk.RadioButton()
			self._radio_format_group = radio
		else:
			radio = Gtk.RadioButton.new_from_widget(self._radio_format_group)
		if wide:
			wide_label = Gtk.Label()
			wide_label.set_markup('<b>' + file_format_label + '</b>')
			radio.add(wide_label)
		else:
			radio.set_label(file_format_label)
		radio.set_halign(Gtk.Align.START)
		self._all_radio_btns[file_format] = radio
		return radio

	############################################################################

	def do_close(self, *args):
		self.destroy()

	def do_cancel(self, *args):
		self.destroy()

	def do_apply(self, *args):
		pass

	def do_prepare(self, *args):
		if self.get_current_page() == 1:
			# TODO regarder les boutons et n'activer que les bons backends
			pass
		elif self.get_current_page() == 2:
			if not self.start_export():
				self.set_current_page(0)
				self.present()
			self.close()

	############################################################################

	def update_css(self, is_active, uri):
		self._backend.update_pandoc_combobox()

	def _show_accurate_style_manager(self, show_css, show_revealjs):
		self.revealjs_manager.full_widget.set_visible(show_revealjs)
		self.css_manager.full_widget.set_visible(show_css)
		self.no_style_label.set_visible(not (show_css or show_revealjs))

	def set_command_for_format(self, output_format):
		if output_format == 'custom':
			command = self._settings.get_string('custom-export')
			self._backend.set_pandoc_command(command)
			self.output_extension = '.pdf' # XXX
			self._show_accurate_style_manager(False, False)
			return

		show_revealjs = output_format == 'revealjs'
		show_css = not show_revealjs and output_format != 'plain'
		self._show_accurate_style_manager(show_css, show_revealjs)

		command = 'pandoc $INPUT_FILE %s -o $OUTPUT_FILE'
		options = ''
		accept_css = True
		if output_format == 'pdf':
			options = '-V geometry=right=2cm -V geometry=left=2cm -V ' \
			                 'geometry=bottom=2cm -V geometry=top=2cm'
			self.output_extension = '.pdf'
		elif output_format == 'revealjs':
			options = '-t revealjs -s --metadata pagetitle=Exported ' + \
			                     '-V revealjs-url=http://lab.hakim.se/reveal-js'
			options = options + ' -V theme=' + self._settings.get_string('revealjs-theme')
			options = options + ' -V transition=' + \
			                   self._settings.get_string('revealjs-transitions')
			if self._settings.get_boolean('revealjs-slide-num'):
				options = options + ' -V slideNumber=true'
				# there are more options but a boolean is enough for me
			self.output_extension = '.html'
			accept_css = False # in fact, it does accept a stylesheet as an
			# option, but the 2 CSS will often be incompatible.
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

	def start_export(self):
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

