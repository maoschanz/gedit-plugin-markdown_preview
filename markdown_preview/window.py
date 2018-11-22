import subprocess
import gi
import os
gi.require_version('WebKit2', '4.0')
from gi.repository import GObject, Gtk, Gedit, Gio, PeasGtk, WebKit2, GLib

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
    import gettext
    gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
    gettext.textdomain('gedit-plugin-markdown-preview')
    _ = gettext.gettext
except:
    _ = lambda s: s
    
class MdPreviewWindow():
	__gtype_name__ = 'MdPreviewWindow'

	def __init__(self, preview_bar):
		self.window = Gtk.Window(title=_("Markdown Preview"))
		self.preview_bar = preview_bar
		self.preview_bar.is_paginated = True
		headerbar = Gtk.HeaderBar(show_close_button=False)
		
		zoom_box = Gtk.Box()
		zoom_box.get_style_context().add_class('linked')
		zoom_out_btn = Gtk.Button().new_from_icon_name('zoom-out-symbolic', Gtk.IconSize.BUTTON)
		self.zoom_current = Gtk.Button(label='100%')
		zoom_in_btn = Gtk.Button().new_from_icon_name('zoom-in-symbolic', Gtk.IconSize.BUTTON)
		zoom_box.add(zoom_out_btn)
		zoom_box.add(self.zoom_current)
		zoom_box.add(zoom_in_btn)
		zoom_out_btn.connect('clicked', self.on_zoom_out)
		self.zoom_current.connect('clicked', self.on_zoom_original)
		zoom_in_btn.connect('clicked', self.on_zoom_in)
		self.on_zoom_original()
		headerbar.pack_start(zoom_box)
		
		self.adj = Gtk.Adjustment(
			lower=0,
			upper=self.preview_bar.page_number+1,
			step_increment=1,
			page_increment=1)
		page_box = Gtk.Box()
		page_box.get_style_context().add_class('linked')
		page_prev_btn = Gtk.Button().new_from_icon_name('go-previous-symbolic', Gtk.IconSize.BUTTON)
		self.page_current = Gtk.ScaleButton(adjustment=self.adj,
			label='1/1',
			relief=Gtk.ReliefStyle.NORMAL,
			value=1)
		self.page_current.connect('value-changed', self.cb_value_changed)
		self.adj.connect('value-changed', self.cb_value_changed)
		page_next_btn = Gtk.Button().new_from_icon_name('go-next-symbolic', Gtk.IconSize.BUTTON)
		page_box.add(page_prev_btn)
		page_box.add(self.page_current)
		page_box.add(page_next_btn)
		page_prev_btn.connect('clicked', self.on_page_previous)
		page_next_btn.connect('clicked', self.on_page_next)
		self.update_page_label()
		headerbar.set_custom_title(page_box)
		
		restore_btn = Gtk.Button().new_from_icon_name('view-restore-symbolic', Gtk.IconSize.BUTTON)
		restore_btn.connect('clicked', self.on_close)
		headerbar.pack_end(restore_btn)
		
		headerbar.show_all()
		self.window.set_titlebar(headerbar)
		self.window.add(self.preview_bar._webview)
		self.window.maximize()
		self.window.connect('destroy', self.restore_preview)
		
		self.preview_bar.on_reload()
		
	def on_close(self, *args):
		self.window.close()
		
	def on_zoom_original(self, *args):
		self.preview_bar.on_zoom_original()
		self.zoom_current.set_label('100%')
		
	def on_zoom_in(self, *args):
		self.zoom_current.set_label(str(int(self.preview_bar.on_zoom_in()*100)) + '%')
		
	def on_zoom_out(self, *args):
		self.zoom_current.set_label(str(int(self.preview_bar.on_zoom_out()*100)) + '%')
		
	def cb_value_changed(self, *args):
		if len(args) == 2:
			self.preview_bar.page_index = int(args[1])
			self.preview_bar.on_reload()
			self.update_page_label()
	
	def on_page_previous(self, *args):
		self.preview_bar.on_previous_page()
		self.update_page_label()
		self.page_current.set_value(self.preview_bar.page_index)
		
	def on_page_next(self, *args):
		self.preview_bar.on_next_page()
		self.update_page_label()
		self.page_current.set_value(self.preview_bar.page_index)
		
	def update_page_label(self):
		self.page_current.set_label(str(int(self.preview_bar.page_index)+1) + '/' \
			+ str(int(self.preview_bar.page_number)))
		
	def restore_preview(self, *args):
		self.window.remove(self.preview_bar._webview)
		self.preview_bar.preview_bar.pack_start(self.preview_bar._webview, expand=True, fill=True, padding=0)
		self.preview_bar._webview.show()
		action = self.preview_bar.parent_plugin.window.lookup_action('md-set-view-mode')
		self.preview_bar.parent_plugin.on_change_view_mode(action, GLib.Variant.new_string('whole'))

##################################################
