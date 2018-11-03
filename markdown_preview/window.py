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

	def __init__(self, gedit_window):
		self.window = Gtk.Window(title=_("Markdown Preview"))
		self.gedit_window = gedit_window
		self.gedit_window.is_paginated = True
		self.gedit_window.on_reload()
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
		
		self.adj = Gtk.Adjustment(lower=1, upper=10, step_increment=1, page_increment=1)
		page_box = Gtk.Box()
#		page_box = Gtk.Box(spacing=5)
		page_box.get_style_context().add_class('linked')
		page_prev_btn = Gtk.Button().new_from_icon_name('go-previous-symbolic', Gtk.IconSize.BUTTON)
		self.page_current = Gtk.ScaleButton(adjustment=self.adj, label='1/1', relief=Gtk.ReliefStyle.NORMAL, value=1)
		self.page_current.connect('value-changed', self.cb_value_changed)
		self.adj.connect('value-changed', self.cb_value_changed)
#		self.page_current = Gtk.Label(label='1/1')
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
		self.window.add(self.gedit_window._webview)
		self.window.maximize()
		self.window.connect('destroy', self.restore_preview)
		
	def on_close(self, *args):
		self.window.close()
		
	def on_zoom_original(self, *args):
		self.gedit_window.on_zoom_original()
		self.zoom_current.set_label('100%')
		
	def on_zoom_in(self, *args):
		self.zoom_current.set_label(str(int(self.gedit_window.on_zoom_in()*100)) + '%')
		
	def on_zoom_out(self, *args):
		self.zoom_current.set_label(str(int(self.gedit_window.on_zoom_out()*100)) + '%')
		
	def cb_value_changed(self, *args):
		self.adj.set_upper(self.gedit_window.page_number)
		if len(args) == 2:
			self.gedit_window.page_index = int(args[1])
			self.gedit_window.on_reload()
			self.update_page_label()
	
	def on_page_previous(self, *args):
		self.gedit_window.on_previous_page()
		self.update_page_label()
		self.page_current.set_value(self.gedit_window.page_index)
		
	def on_page_next(self, *args):
		self.gedit_window.on_next_page()
		self.update_page_label()
		self.page_current.set_value(self.gedit_window.page_index)
		
	def update_page_label(self):
		self.page_current.set_label(str(int(self.gedit_window.page_index)+1) + '/' \
			+ str(int(self.gedit_window.page_number)))
		
	def restore_preview(self, *args):
		self.window.remove(self.gedit_window._webview)
		self.gedit_window.preview_bar.pack_start(self.gedit_window._webview, expand=True, fill=True, padding=0)
		self.gedit_window._webview.show()
		self.gedit_window.is_paginated = False
		self.gedit_window.on_reload()
		
##################################################
