#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygtk
import sys
pygtk.require('2.0')

import gtk
import glib
import gnome.ui
import appindicator
import subprocess
import os
import random
import logging
import logging.config
import traceback
from xml.dom import minidom
import base64
import codecs

WALLPAPER_PATH = "/usr/share/backgrounds"
VERSION="1.2.0.0"
NAME="mikukabe"

class ConfigXML:
    OptionList = {   "wallpaper_path":"/usr/share/backgrounds",
                            "interval":"15",    #分単位
                            "use_wallpaper":"",
                            "startup":"True",
                            "style":"1",
                            "styleName":"scaled"}
    AppName = "mikukabe"
    ConfigPath = "/.config/mikukabe.xml"
    Options = {}    #オプション値の辞書
    domobj = None

    def __init__(self, read):
        #print "ConfigXML"
        if read == True :
            try:
                self.domobj = minidom.parse(os.path.abspath(os.path.expanduser("~") + self.ConfigPath))
                options = self.domobj.getElementsByTagName("options")
                for opt in options :
                    for op,defVal in self.OptionList.iteritems():
                        elm = opt.getElementsByTagName(op)
                        if len(elm) > 0 :
                            self.Options[op] = self.getText(elm[0].childNodes)
                        else:
                            self.Options[op] = defVal
            except:
                for op,defVal in self.OptionList.iteritems():
                    self.Options[op] = defVal

    def getText(self,nodelist):
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                text = str(node.data)
                text = text.rstrip(" \t\n")
                text = text.lstrip(" \t\n")
                rc = rc + text
        return rc

    def GetOption(self, optName ):
        if optName == "password":
            return str(base64.b64decode(self.Options[optName]))
        else:
            try:
                return str(self.Options[optName])
            except:
                return str(self.OptionList[optName])

    def SetOption(self, optName, value ):
        if optName == "password":
            val = base64.b64encode(value)
            self.Options[optName] = val
        else:
            self.Options[optName] = value

    def Write(self):
        try:
            impl = minidom.getDOMImplementation()
            newdoc = impl.createDocument(None, self.AppName, None)
            root = newdoc.documentElement
            opts = newdoc.createElement("options")
            root.appendChild(opts)
            for op in self.OptionList.keys():
                opt = newdoc.createElement(op)
                opts.appendChild(opt)
                text = newdoc.createTextNode(str(self.Options[op]))
                opt.appendChild(text)
            file = codecs.open(os.path.abspath(os.path.expanduser("~") + self.ConfigPath), 'wb', encoding='utf-8')
            newdoc.writexml(file, '', '\t', '\n', encoding='utf-8')
        except:
            logging.error(traceback.format_exc())

class Mikukabe:

    wallpaper_list = []
    use_wallpaper_list = []
    #timeout_interval = 10
    timeout_interval = 15*60

    def __init__(self):
        logging.debug("__init__")
        self._createIcon()
        #オプションを読み込み
        global WALLPAPER_PATH
        conf = ConfigXML(True)
        WALLPAPER_PATH = conf.GetOption("wallpaper_path")
        self.timeout_interval = float(conf.GetOption("interval"))*60
        uselist = conf.GetOption("use_wallpaper")
        self.wallpaperStyle = conf.GetOption("style")
        self.wallpaperStyleName = conf.GetOption("styleName")
        if len(uselist) > 0:
            use_wallpaper_list = eval(uselist)
        #ダイアログを作成
        self.wTree = gtk.Builder()
        self.wTree.add_from_file(os.path.dirname(os.path.abspath(__file__)) + "/mikukabe.glade")
        preferencesDialog = self.wTree.get_object('properties')
        self.selectedFolder = self.wTree.get_object("FS_FOLDER")
        #self.selectedFolder.set_filename(WALLPAPER_PATH+"/")
        self.selectedFolder.set_current_folder(WALLPAPER_PATH+"/")
        self.intervalMinute = self.wTree.get_object("SPN_INTERVAL")
        self.intervalMinute.set_value(self.timeout_interval/60.0)
        self.startupChange = self.wTree.get_object("CB_STARTUP_CHANGE")
        self.startup = eval(conf.GetOption("startup"))
        self.startupChange.set_active(self.startup)
        self.wStyle = self.wTree.get_object("cmbStyle")
        self.lscvType = self.wTree.get_object ("listStyle")
        self.wStyle.set_model(self.lscvType)
        cell = gtk.CellRendererText()
        self.wStyle.pack_start(cell, True)
        self.wStyle.add_attribute(cell, 'text', 0)
        self.preferences = preferencesDialog
        #Create our dictionay and connect it
        dic = { "on_BTN_OK_clicked" : self.on_BTN_OK_clicked,
                   "on_BTN_CANCEL_clicked" : self.on_BTN_CANCEL_clicked,
                   "on_properties_delete_event" : self.on_properties_delete_event }
        self.wTree.connect_signals(dic)
        #壁紙一覧を作成
        tmplist = os.listdir(WALLPAPER_PATH+"/")
        self.wallpaper_list = [ WALLPAPER_PATH+"/" +x for x in tmplist if x.find(".jpg") >= 0 or x.find(".JPG") >= 0 or x.find(".png") >= 0 or x.find(".PNG") >= 0]
        logging.debug(str(self.wallpaper_list))
        self.timeout = glib.timeout_add_seconds(int(self.timeout_interval),self.timeout_callback,self)
        self.wStyle.set_active(int(self.wallpaperStyle))
        self.ind = appindicator.Indicator ("Mikukabe",
                                    "mikukabe",
                                    appindicator.CATEGORY_APPLICATION_STATUS)
        self.ind.set_icon_theme_path("/tmp")
        self.ind.set_attention_icon("mikukabe")
        self.ind.set_status (appindicator.STATUS_ACTIVE)
        self.create_menu()
        if self.startup:
            self._changeWallPaper()

    def __getitem__(self, key):
        return self.wTree.get_object (key)

    def on_BTN_OK_clicked(self,widget):
        global WALLPAPER_PATH
        WALLPAPER_PATH = self.selectedFolder.get_filename()
        print WALLPAPER_PATH
        conv_type = self.wStyle.get_active()
        print conv_type
        row = self.lscvType[conv_type]
        self.wallpaperStyle = conv_type
        self.wallpaperStyleName = row[0]
        self.timeout_interval = self.intervalMinute.get_value()*60
        self.startup = self.startupChange.get_active()
        self._saveConf()
        self.preferences.hide()
        glib.source_remove(self.timeout)
        self.timeout = glib.timeout_add_seconds(int(self.timeout_interval),self.timeout_callback,self)

    def on_BTN_CANCEL_clicked(self,widget):
        self.selectedFolder.set_filename(WALLPAPER_PATH+"/")
        self.intervalMinute.set_value(self.timeout_interval/60)
        self.preferences.hide()

    def on_properties_delete_event(self,widget,event):
        widget.hide()
        return gtk.TRUE

    def _createIcon(self):
        logging.debug("_createIcon")
        wallpaper = self._getWallpaper()
        logging.debug("wallpaper:"+wallpaper)
        size = 24
        pixbuf = gtk.gdk.pixbuf_new_from_file(wallpaper)
        x = float(pixbuf.get_width())
        y = float(pixbuf.get_height())
        aspect = y / x
        pixbuf2 = pixbuf.scale_simple(size, int(size*aspect),gtk.gdk.INTERP_BILINEAR )
        del pixbuf
        pixbuf2.save("/tmp/mikukabe.png","png")
        pixbuf2.save("/tmp/mikukabe.png","png")
        del pixbuf2

    def _setWallpaper(self,WallpaperLocation, wallpaperStyle):
        subprocess.Popen(["gconftool-2", "--type","string","-s", "/desktop/gnome/background/picture_filename",WallpaperLocation], stdout=subprocess.PIPE)
        subprocess.Popen(["gconftool-2", "--type","string","-s", "/desktop/gnome/background/picture_options",wallpaperStyle], stdout=subprocess.PIPE)

    def _getWallpaper(self):
        retcall = subprocess.Popen(["gconftool-2", "-g", "/desktop/gnome/background/picture_filename"], stdout=subprocess.PIPE)
        return retcall.stdout.readline().strip('\n')

    def _changeWallPaper(self):
        wlist = self.wallpaper_list
        if len(self.use_wallpaper_list) > 0:
            chkSet = set(self.use_wallpaper_list)
            wlist = [x for x in self.wallpaper_list if x not in chkSet]
            #print str(len(wlist))
            if len(wlist) == 0:
                self.use_wallpaper_list = []
                wlist = self.wallpaper_list
        #print wlist
        sw = random.randint(0,len(wlist)-1)
        #print str(sw) +";" +wlist[sw]
        self.use_wallpaper_list.append(wlist[sw])
        self._setWallpaper(wlist[sw] , self.wallpaperStyleName)
        self._createIcon()
        self._saveConf()
        self.ind.set_attention_icon("mikukabe00")
        self.ind.set_attention_icon("mikukabe")
        self.ind.set_status (appindicator.STATUS_ACTIVE)


    def _saveConf(self):
        #変更結果を保存
        global WALLPAPER_PATH
        conf = ConfigXML(False)
        conf.SetOption("wallpaper_path",WALLPAPER_PATH)
        conf.SetOption("interval",str(self.timeout_interval/60))
        conf.SetOption("use_wallpaper",str(self.use_wallpaper_list))
        conf.SetOption("startup",str(self.startup))
        conf.SetOption("style",self.wallpaperStyle)
        conf.SetOption("styleName",self.wallpaperStyleName)
        conf.Write()

    def showMenu(self,widget, event, applet):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            #右クリック
            widget.emit_stop_by_name("button_press_event")
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            #左クリック
            self._changeWallPaper()

    def changeNext(self,widget,event):
        self._changeWallPaper()

    def create_menu(self):
        # create a menu
        menu = gtk.Menu()
        # create some
        menu_items0 = gtk.MenuItem("切替")
        menu_items1 = gtk.MenuItem("設定")
        menu_items2 = gtk.MenuItem("情報")
        menu_items3 = gtk.MenuItem("終了")
        menu_items0.connect("activate", self.changeNext, "切替")
        menu_items1.connect("activate", self.properties, "設定")
        menu_items2.connect("activate", self.showAboutDialog, "情報")
        menu_items3.connect("activate", gtk.mainquit, "情報")
        menu.append(menu_items0)
        menu.append(menu_items1)
        menu.append(menu_items2)
        menu.append(menu_items3)
        menu_items0.show()
        menu_items1.show()
        menu_items2.show()
        menu_items3.show()

        self.ind.set_menu(menu)

    def showAboutDialog(self,*arguments, **keywords):
        if os.path.exists("/usr/share/mikukabe/mikukabe.png") == True:
            imagePath = "/usr/share/mikukabe/mikukabe.png"
        elif os.path.exists(os.path.dirname(os.path.abspath(__file__)) + "/mikukabe.png") == True:
            imagePath = os.path.dirname(os.path.abspath(__file__)) + "/mikukabe.png"
        self.logo = gtk.Image()
        self.logo.set_from_file(imagePath)
        self.logo_pixbuf = self.logo.get_pixbuf()
        self.about = gnome.ui.About("みくかべ♪",VERSION,"GPLv3","定期的に壁紙を変更します。",["かおりん"],["かおりん"],"かおりん",self.logo_pixbuf)
        self.about.show_all()

    def properties(self,event,data=None):
        self.preferences.show()

    def timeout_callback(self,event):
        self._changeWallPaper()
        return True


if __name__ == '__main__':
    Mikukabe()
    gtk.main()
