# tags_manager.py
# GPL v3

import gi
from gi.repository import Gtk

class MdTagsManager():

	def __init__(self, view_plugin):
		self._view_plugin = view_plugin

	############################################################################

	def add_block_tags(self, start_tag, end_tag=None):
		start, end = self._find_block_iters()

		if end_tag is None:
			end_tag = start_tag
		start_tag = start_tag + "\n"
		end_tag = "\n" + end_tag
		self._add_tags_characters(start_tag, end_tag, start, end)

	def remove_line_tags(self, start_tag, end_tag=None):
		"""Remove `start_tag` from the beginning of the line; and `end_tag` from
		the end of the line."""
		if end_tag is None:
			end_tag = start_tag
		# TODO v4

	def add_line_tags(self, start_tag, add_intermediate_space=True):
		"""Add `start_tag` at the beginning of the line."""
		start, end = self._find_block_iters()

		if add_intermediate_space:
			start_tag = start_tag + " "

		# There is no "closing" tag to add in the case of `add_line_tags`
		self._add_tags_characters(start_tag, '', start, end)

	def add_word_tags(self, tag_both):
		"""Add a tag at both sides of a selected bit of text."""
		document = self._get_active_document_buffer()
		selection = document.get_selection_bounds()
		if selection != ():
			(start, end) = selection
		else:
			return
		self._add_tags_characters(tag_both, tag_both, start, end)

	############################################################################

	def insert_link(self):
		# What to insert
		start_tag = "["
		end_tag = "]()"

		# Where to insert
		self._insert_around_alt_text(start_tag, end_tag)

	def insert_picture(self, window):
		# Building a FileChooserDialog for pictures
		file_chooser = Gtk.FileChooserDialog(_("Select a picture"), window,
			Gtk.FileChooserAction.OPEN,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		onlyPictures = Gtk.FileFilter()
		onlyPictures.set_name("Pictures")
		onlyPictures.add_mime_type('image/*')
		file_chooser.set_filter(onlyPictures)
		response = file_chooser.run()

		# Aborting
		if response != Gtk.ResponseType.OK:
			file_chooser.destroy()
			return

		# What to insert
		start_tag = "!["
		end_tag = "](" + file_chooser.get_filename() + ")"
		file_chooser.destroy()

		# Where to insert
		self._insert_around_alt_text(start_tag, end_tag)

	def insert_table(self, nb_columns):
		document = self._get_active_document_buffer()
		table_markdown = "\n|" + nb_columns * " header  |" + \
		                 "\n|" + nb_columns * "---------|" + \
		                 "\n|" + nb_columns * " content |" + "\n"
		iterator = doc.get_iter_at_mark(document.get_insert())
		document.insert(iterator, table_markdown)

	############################################################################

	def _insert_around_alt_text(self, start_tag, end_tag):
		"""Insert around a given selection IF it's on a single line. Otherwise,
		or if there is no selection, insert as a single string."""
		document = self._get_active_document_buffer()
		start = document.get_iter_at_mark(document.get_insert())
		end = None
		# by default, insert as a tag with empty brackets. But if a part of a
		# line is selected, it will be the image/link's alt text.
		selection = document.get_selection_bounds()
		if selection != ():
			(start_select, end_select) = selection
			number_lines = self._get_n_lines(start_select, end_select)
			if number_lines == 1:
				(start, end) = (start_select, end_select)

		# Actually insert
		if end is None:
			document.insert(start, start_tag + end_tag)
		else:
			self._add_tags_characters(start_tag, end_tag, start, end)

	def _add_tags_characters(self, start_tag, end_tag, start, end):
		document = self._get_active_document_buffer()
		start_mark = document.create_mark('start', start, True)
		current_mark = document.create_mark('iter', start, False)
		end_mark = document.create_mark('end', end, False)
		number_lines = self._get_n_lines(start, end)
		document.begin_user_action()

		for i in range(0, number_lines):
			iterator = document.get_iter_at_mark(current_mark)
			if not iterator.ends_line():
				document.insert(iterator, start_tag)
				if end_tag is not None:
					if i != number_lines -1:
						iterator = document.get_iter_at_mark(current_mark)
						iterator.forward_to_line_end()
						document.insert(iterator, end_tag)
					else:
						iterator = document.get_iter_at_mark(end_mark)
						document.insert(iterator, end_tag)
			iterator = document.get_iter_at_mark(current_mark)
			iterator.forward_line()
			document.delete_mark(current_mark)
			current_mark = document.create_mark('iter', iterator, True)

		document.end_user_action()

		# Change the selection to include the newly inserted opening tag in it
		document.delete_mark(current_mark)
		new_start = document.get_iter_at_mark(start_mark)
		new_end = document.get_iter_at_mark(end_mark)
		if new_start.compare(new_end) == 0:
			# An insertion where nothing was selected: the "left_gravity"
			# properties given to `create_mark` are not enough to manage the
			# the situation! We move the `new_start` to select both tags.
			self._backward_tag(new_start, end_tag)
		document.select_range(new_start, new_end)
		document.delete_mark(start_mark)
		document.delete_mark(end_mark)

	def _get_n_lines(self, start, end):
		return end.get_line() - start.get_line() + 1

	def _forward_tag(self, iterator, tag):
		iterator.forward_chars(len(tag))

	def _backward_tag(self, iterator, tag):
		iterator.backward_chars(len(tag))

	def _find_block_iters(self):
		document = self._get_active_document_buffer()
		selection = document.get_selection_bounds()
		if selection != ():
			(start, end) = selection
		else:
			start = document.get_iter_at_mark(document.get_insert())
			end = document.get_iter_at_mark(document.get_insert())

		# The "start" boundary should be the start of the first line of the
		# selection, except if no character in this first line is selected.
		if start.ends_line():
			start.forward_line()
		elif not start.starts_line():
			start.set_line_offset(0)

		# The "end" boundary should be the end of the last line of the
		# selection, except if no character in this last line is selected.
		if end.starts_line():
			end.backward_char()
		elif not end.ends_line():
			end.forward_to_line_end()

		return start, end

	def _get_active_document_buffer(self):
		return self._view_plugin.view.get_buffer()

	############################################################################
################################################################################

