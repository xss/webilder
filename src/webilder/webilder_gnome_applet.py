#!/usr/bin/env python
'''
File    : webilder_gnome_applet.py
Author  : Nadav Samet
Contact : thesamet@gmail.com
Date    : 2010 Jun 17

Description : Webilder panel applet for GNOME.
'''
import pygtk
pygtk.require('2.0')
import pkg_resources

from webilder.base_applet import BaseApplet
from webilder.config import config
from webilder import AboutDialog
from webilder import config_dialog
from webilder import DownloadDialog
from webilder import __version__
from webilder import WebilderDesktop

import sys
import gtk
import gnomeapplet
import gnome
import gobject


# Set this to False if you don't want the software to check
# for updates.
#
# No information, except of the version request itself is sent
# to Webilder's server.

class WebilderApplet(BaseApplet):
    """Implementation for Webilder GNOME panel applet."""
    def __init__(self, applet, _iid):
        BaseApplet.__init__(self)
        gnome.init('WebilderApplet', __version__)
        self.applet = applet
        self.tooltips = gtk.Tooltips()
        self.tooltips.enable()
        self.evtbox = gtk.EventBox()
        self.icon = gtk.gdk.pixbuf_new_from_file(
            pkg_resources.resource_filename(__name__, 'ui/camera48.png'))
        self.icon_green = gtk.gdk.pixbuf_new_from_file(
            pkg_resources.resource_filename(__name__, 'ui/camera48_g.png'))

        self.applet_icon = gtk.Image()
        self.scaled_icon = self.icon.scale_simple(16, 16,
                gtk.gdk.INTERP_BILINEAR)
        self.scaled_icon_green = self.icon_green.scale_simple(16, 16,
                gtk.gdk.INTERP_BILINEAR)

        self.applet_icon.set_from_pixbuf(self.scaled_icon)
        self.evtbox.add(self.applet_icon)
        self.applet.add(self.evtbox)
        # ### Item 7 new in following list
        self.propxml = _("""
    <popup name="button3">
        <menuitem name="Item 1" verb="Browse" label="_Browse Collection" pixtype="stock"
pixname="gtk-directory"/>
        <menuitem name="Item 2" verb="NextPhoto" label="_Next Photo" pixtype="stock"
pixname="gtk-go-forward"/>
        <menuitem name="Item 3" verb="Leech" label="_Download Photos" pixtype="filename"
pixname="%s"/>
        <menuitem name="Item 7" verb="InfoCurrent" label="_Info on Current" pixtype="stock" pixname="gtk-dialog-info"/>
        <menuitem name="Item 6" verb="DeleteCurrent" label="_Delete Current" pixtype="stock" pixname="gtk-delete"/>
        <menuitem name="Item 4" verb="Pref" label="_Preferences" pixtype="stock"
pixname="gtk-preferences"/>
        <menuitem name="Item 5" verb="About" label="_About" pixtype="stock" pixname="gnome-stock-about"/>
        </popup>
    """) % pkg_resources.resource_filename(__name__, 'ui/camera16.png')

        self.applet.connect("change-size", self.on_resize_panel)
        self.applet.connect("button-press-event", self.on_button_press)

        self.verbs = [
            ( "Pref", self.preferences ),
            ( "About", self.about),
            ( "Browse", self.browse),
            ( "NextPhoto", self.next_photo),
            ( "Leech", self.leech),
            ( "DeleteCurrent", self.delete_current),
            ( "InfoCurrent", self.info_current)] # ### "InfoCurrent" is new
        self.applet.setup_menu(self.propxml, self.verbs, None)
        self.applet.show_all()
        gobject.timeout_add(60*1000, self.timer_event)
        self.photo_browser = None
        self.download_dlg = None

# ### NEW function start
    def info_current(self, *_args):
        """Opens the photo properties window."""
        import os, time, commands
        from webilder.webshots.wbz import parse_metadata
        from webilder.uitricks import UITricks, open_browser

        currentfile = commands.getoutput('/usr/bin/gconftool-2 -g /desktop/gnome/background/picture_filename')

        if self.image_file == currentfile:
            currentinfo = self.info_file
            try:
                fileobj = open(currentinfo, 'r')
                infodata = parse_metadata(fileobj.read())
                fileobj.close()
            except IOError:
                infodata = {}

        else:
            import getpass
            wbtestpath = '/home/' + getpass.getuser() + '/.webilder/Collection/'
            wbtest = currentfile.startswith(wbtestpath)
            if wbtest == True:
                currentinfo = os.path.splitext(currentfile)[0] + '.inf'
                try:
                    fileobj = open(currentinfo, 'r')
                    infodata = parse_metadata(fileobj.read())
                    fileobj.close()
                except IOError:
                    infodata = {}
            else:
                try:
                    infodata = parse_metadata("url=--\ncredit=--\ntitle=--\ntags=--\nalbumTitle=--\n")
                except IOError:
                    infodata = {}

        applet_win = UITricks('ui/webilder.glade', 'PhotoPropertiesDialog')
        applet_win.title.set_markup('<b>%s</b>' % infodata['title'])
        applet_win.album.set_markup(infodata['albumTitle'])
        applet_win.file.set_text(currentfile)
        applet_win.tags.set_text(infodata['tags'])
        applet_win.size.set_text(_('%.1f KB') % (os.path.getsize(currentfile) / 1024.0))
        applet_win.date.set_text(time.strftime('%c', time.localtime(os.path.getctime(currentfile))))
        applet_win.url.set_text(infodata['url'])

        applet_win.closebutton.connect('clicked', lambda *args: applet_win.destroy())
        applet_win.show()
# ### NEW function end

    def set_tooltip(self, text):
        self.tooltips.enable()
        self.tooltips.set_tip(self.applet, text)

    def preferences(self, _object, _menu):
        """Opens the preferences dialog."""
        config_dialog.ConfigDialog().run_dialog(config)

    def about(self, _object, _menu):
        """Opens the about dialog."""
        AboutDialog.show_about_dialog(_('Webilder Applet'))

    def leech(self, _object, _menu):
        """Starts downloading photos."""
        def remove_reference(*_args):
            """Removes reference to the download dialog so we will not it is
            not running."""
            self.download_dlg = None

        if self.download_dlg:
            return
        self.download_dlg = DownloadDialog.DownloadProgressDialog(config)
        self.download_dlg.top_widget.connect('destroy', remove_reference)
        self.download_dlg.show()
        self.applet_icon.set_from_pixbuf(self.scaled_icon)
        self.tooltips.disable()

    def on_resize_panel(self, _widget, size):
        """Called when the panel is resized so we can scale our icon."""
        self.scaled_icon = self.icon.scale_simple(size - 4, size - 4,
            gtk.gdk.INTERP_BILINEAR)
        self.scaled_icon_green = self.icon_green.scale_simple(size - 4,
                                                              size - 4,
            gtk.gdk.INTERP_BILINEAR)
        self.applet_icon.set_from_pixbuf(self.scaled_icon)

    def on_button_press(self, _widget, event):
        """Called when the user clicks on the applet icon."""
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            return False
        elif event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            if not self.photo_browser:
                self.browse(None, None)
            else:
                toggle_window_visibility(self.photo_browser.top_widget)

    def browse(self, _object, _menu):
        """Opens the photo browser."""
        if not self.photo_browser:
            self.photo_browser = WebilderDesktop.WebilderDesktopWindow()
            self.photo_browser.top_widget.connect("destroy",
                                                  self.photo_browser_destroy)
        else:
            self.photo_browser.top_widget.show_all()

    def photo_browser_destroy(self, _event):
        """Called when the photo browser is closed."""
        self.photo_browser.destroy()
        self.photo_browser = None

def webilder_applet_factory(applet, iid):
    """Instantiates a webilder applet."""
    WebilderApplet(applet, iid)
    return True

def toggle_window_visibility(window):
    """Hides and show the photo browser."""
    visible = window.get_property('visible')
    if visible:
        window.hide()
    else:
        window.show_all()

def main():
    """Entrypoint for the panel applet."""
    gtk.gdk.threads_init()

    if len(sys.argv) == 2 and sys.argv[1] == "run-in-window":
        print "here"
        main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        main_window.set_title(_("Webilder Applet Window"))
        main_window.connect("destroy", gtk.main_quit)
        app = gnomeapplet.Applet()
        WebilderApplet(app, None)
        app.reparent(main_window)
        main_window.show_all()
        gtk.main()
        sys.exit()
    else:
        gnomeapplet.bonobo_factory("OAFIID:GNOME_WebilderApplet_Factory",
                                 gnomeapplet.Applet.__gtype__,
                                 "webilder-hello", "0", webilder_applet_factory)
