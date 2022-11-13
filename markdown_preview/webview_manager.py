# webview_manager.py
# GPL v3

import gi
gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, WebKit2
from .find_manager import MdFindManager
from .utils import init_gettext

_ = init_gettext()

SCRIPT_SCROLL_TO_CURSOR = """
window.document.body.scrollTop = %d;
var cursorRow = %d;
var cursorColumn = %d;
function setCursorPositionPandoc () {
   var dataPosElements = window.document.querySelectorAll("[data-pos]");
   var dataPosRegExp = new RegExp(".*@(?<start_row>[0-9]*):(?<start_column>[0-9]*)-(?<end_row>[0-9]*):(?<end_column>[0-9]*)");
   var values = "";
   for (let e of dataPosElements) {
      var dataPos = e.getAttribute("data-pos");
      var matches = dataPosRegExp.exec(dataPos, "g");

      if (!matches) {
         continue;
      }

      values += cursorRow+" "+cursorColumn+"\\n";
      values += startRow+" "+startColumn+" "+endRow+" "+endColumn+"\\n";

      var startRow = parseInt(matches.groups.start_row);
      var startColumn = parseInt(matches.groups.start_column);
      var endRow = parseInt(matches.groups.end_row);
      var endColumn = parseInt(matches.groups.end_column);
      if (startRow<=cursorRow && cursorRow<=endRow &&
         (startRow!==cursorRow || startColumn<=cursorColumn) &&
          (endRow!==cursorRow || cursorColumn<=endColumn)) {
         e.scrollIntoViewIfNeeded();
         return true;
      }
   }
   return false;
}

function setCursorPositionPythonMarkdown() {
   var sourceLineElements = window.document.querySelectorAll("[source-line]");
   var highestLowerBoundLine = -1;
   var highestLowerBoundElement = null;
   for (let e of sourceLineElements) {
      let sourceLine = parseInt(e.getAttribute("source-line"));
      if (sourceLine<=cursorRow && highestLowerBoundLine<sourceLine) {
         highestLowerBoundLine = sourceLine;
         highestLowerBoundElement = e;
      }
   }
   if (highestLowerBoundElement) {
      highestLowerBoundElement.scrollIntoViewIfNeeded();
      return true;
   }
   return false;
}

let cursorUpdateFunctions = [setCursorPositionPandoc, setCursorPositionPythonMarkdown];
for (let f of cursorUpdateFunctions) {
   try {
      if (f ()) {
         break;
      }
   }
   catch (e) {
      window.alert(e);
   }
}
"""

################################################################################

class MdWebViewManager():

	def __init__(self):
		self._scroll_level = 0
		self.cursor_row = 0
		self.cursor_column = 0

		# TODO remember the scroll level in the Gedit.View objects

		self._webview = WebKit2.WebView()
		self._webview.get_settings().set_property('enable_javascript', True)

		self._handlers = []
		id2 = self._webview.connect('context-menu', self.on_context_menu)
		id3 = self._webview.connect('mouse-target-changed', self.on_remember_scroll)
		id4 = self._webview.connect('load-changed', self.on_restore_scroll)
		self._handlers.append(id2)
		self._handlers.append(id3)
		self._handlers.append(id4)

	def set_cursor_position (self, row, column):
		self.cursor_row = row
		self.cursor_column = column

	def add_find_manager(self, ui_builder):
		options = WebKit2.FindOptions.CASE_INSENSITIVE
		MdFindManager(ui_builder, self._webview.get_find_controller(), options)

	def disconnect_handlers(self):
		self._webview.disconnect(self._handlers[2])
		self._webview.disconnect(self._handlers[1])
		self._webview.disconnect(self._handlers[0])

	def load_bytes_for_uri(self, bytes_content, uri):
		self._webview.load_bytes(bytes_content, 'text/html', 'UTF-8', uri)

	############################################################################
	# Printing #################################################################

	def print_webview(self, known_destination=None):
		operation = WebKit2.PrintOperation.new(self._webview)

		if known_destination is None:
			operation.run_dialog()
		else:
			print_settings = Gtk.PrintSettings()
			file_printer_name = self._get_file_printer_name()
			if file_printer_name:
				print_settings.set_printer(file_printer_name)
			else:
				print_settings.set_printer("Print to file")
			print_settings.set(Gtk.PRINT_SETTINGS_OUTPUT_FILE_FORMAT, 'pdf')
			print_settings.set(Gtk.PRINT_SETTINGS_OUTPUT_URI, known_destination)
			operation.set_print_settings(print_settings)

			if file_printer_name:
				# Print directly to the destination without showing the dialog
				operation.print_()
				# FIXME dans ce cas il a les mêmes dimensions que la webview ??
			else:
				operation.run_dialog()
			# FIXME sometimes there is a segfault anyway????

	def _get_file_printer_name(self):
		return None # impossible to do...

	############################################################################
	# Javascript for the scroll level ##########################################

	def on_remember_scroll(self, *args):
		js = 'window.document.body.scrollTop'
		self._webview.run_javascript(js, None, self.javascript_finished, None)
		return

	def on_restore_scroll(self, *args):
		self._webview.run_javascript(SCRIPT_SCROLL_TO_CURSOR %(self._scroll_level,
                                             self.cursor_row, self.cursor_column),
                                             None, None, None)
		return

	def javascript_finished(self, webview, result, user_data):
		js_result = webview.run_javascript_finish(result)
		if js_result is not None:
			value = js_result.get_js_value()
			if not value.is_undefined():
				self._scroll_level = value.to_int32()

	############################################################################
	# Context menu #############################################################

	def build_context_item(self, label, action_name):
		gedit_window = self._webview.get_toplevel()
		gio_action = gedit_window.lookup_action(action_name)
		if gio_action is None:
			print("Error : the action '" + action_name + "' doesn't exist.")
			return None
		return WebKit2.ContextMenuItem.new_from_gaction(gio_action, label, None)

	def remove_at_position(self, context_menu, position):
		context_menu.remove( context_menu.get_item_at_position(position) )

	def on_context_menu(self, a, context_menu, c, hit_test_result):
		special_items = False
		openLinkWithItem = self.build_context_item(_("Open link in browser"), \
		                                               'md-prev-open-link-with')
		openImageWithItem = self.build_context_item(_("Open image in browser"), \
		                                              'md-prev-open-image-with')
		if hit_test_result.context_is_link() and hit_test_result.context_is_image():
			special_items = True
			self.remove_at_position(context_menu, 6) # save image as
			self.remove_at_position(context_menu, 5) # open image in a new window
			self.remove_at_position(context_menu, 2) # download link target
			self.remove_at_position(context_menu, 1) # open link in new window
			self.link_uri_to_open = hit_test_result.get_link_uri()
			self.image_uri_to_open = hit_test_result.get_image_uri()
			context_menu.insert(openLinkWithItem, 2)
			context_menu.insert(openImageWithItem, 6)
		elif hit_test_result.context_is_link():
			special_items = True
			self.remove_at_position(context_menu, 2) # download link target
			self.remove_at_position(context_menu, 1) # open link in new window
			self.link_uri_to_open = hit_test_result.get_link_uri()
			context_menu.append(openLinkWithItem)
		elif hit_test_result.context_is_image():
			special_items = True
			self.remove_at_position(context_menu, 0) # open image in a new window
			self.image_uri_to_open = hit_test_result.get_image_uri()
			context_menu.append(openImageWithItem)
		elif hit_test_result.context_is_selection():
			special_items = True

		context_menu.append(WebKit2.ContextMenuItem.new_separator())
		if not special_items:
			context_menu.remove_all()
		reloadItem = self.build_context_item(_("Reload the preview"), \
		                                                       'md-prev-reload')
		context_menu.append(reloadItem)
		return False

	def on_open_link_with(self, *args):
		Gtk.show_uri(None, self.link_uri_to_open, 0)

	def on_open_image_with(self, *args):
		Gtk.show_uri(None, self.image_uri_to_open, 0)

	############################################################################
	# Zoom #####################################################################

	def on_zoom_in(self, *args):
		if self._webview.get_zoom_level() < 10:
			self._webview.set_zoom_level(self._webview.get_zoom_level() + 0.1)
		return self._webview.get_zoom_level()

	def on_zoom_out(self, *args):
		if self._webview.get_zoom_level() > 0.15:
			self._webview.set_zoom_level(self._webview.get_zoom_level() - 0.1)
		return self._webview.get_zoom_level()

	def on_zoom_original(self, *args):
		self._webview.set_zoom_level(1)

	############################################################################
################################################################################

