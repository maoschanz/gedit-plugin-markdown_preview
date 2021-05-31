# find_manager.py
# GPL v3

from .utils import init_gettext

_ = init_gettext()

class MdFindManager():

	def __init__(self, ui_builder, find_controller, find_options):
		self._find_options = find_options

		self._count_label = ui_builder.get_object('count_label')

		search_entry = ui_builder.get_object('search_entry')
		search_entry.connect('search-changed', self.on_search_changed)

		ui_builder.get_object('up_btn').connect('clicked', self.on_search_up)
		ui_builder.get_object('down_btn').connect('clicked', self.on_search_down)

		self._find_controller = find_controller
		self._find_controller.connect('counted-matches', self.on_count_change)

	def on_search_changed(self, *args):
		text = args[0].get_text()
		self._find_controller.count_matches(text, self._find_options, 100)
		self._find_controller.search(text, self._find_options, 100)

	def on_search_up(self, btn):
		self._find_controller.search_previous()

	def on_search_down(self, btn):
		self._find_controller.search_next()

	def on_count_change(self, find_ctrl, number):
		if number > 100:
			self._count_label.set_text(_("More than 100 results"))
		else:
			self._count_label.set_text(_("%s results") % number)

	############################################################################
################################################################################

