import gtk, os
from uiloader import UILoader
from dfeet._ui.dbustoany import Dbus2Xml, Xml2Any
from dfeet._util import get_xslt_dir

XSLT_DIR = get_xslt_dir()

(NONE,
     XML,
     PYDBUS,
     PYDBUSDECORATOR
 ) = XLST_TYPES = [
    {'name': 'Export',
     'title':'Choose one xslt file'},
    {'name': 'Export as xml',
     'title':'Export as dbus introspection xml'},
    {'name': 'Export as python',
     'title': 'Export as python code',
     'file': XSLT_DIR + 'pydbusclient.xsl'},
    {'name': 'Export as pydbusdecorator',
     'title': 'Export as python code (require pydbusdecorator)',
     'file': XSLT_DIR + 'pydbusdecorator.xsl'},
]

LEN_XLST_TYPES = len(XLST_TYPES)
(NONEN,
 XMLN,
 PYDBUSN,
 PYDBUSDECORATORN) = range(LEN_XLST_TYPES)

class ExportInterfaceDialog(object):
    '''
    Interface that let users export dbus interface as something.
    Since dbus specification recommends that interfaces had introspection method that return
    interface methods, properties e signals as xml. This interface get xml and some xslt then
    write result in somewhere.
    
    To help users are three XSLT included:
    XML: does nothing, just export result of instrospection method
    PYDBUS: export as python dbus code
    PYDBUSDECORATOR: export as python but require pydbusdecoretor to be used as code
    
    To be more flexible with user that know xslt:
    NONE: Can be used, with this user choose xslt

    '''

    def __init__(self, busname, buspath, busiface=None, xslttype=0):
        signal_dict = {
                        'export_dbus_path_cb' : self.export_cb,
                        'export_dialog_close_cb': self.close_cb,
                        'chooserforxlst_file_set_cb': self.choose_file_Cb,
                        'chooserforresult_file_set_cb': self.choose_file_Cb,
                      }
        ui = UILoader(UILoader.UI_EXPORTDIALOG)
        self.dialog = ui.get_root_widget()
        self._lblbusname = ui.get_widget('busname')
        self._lblobjectpath = ui.get_widget('objectpath')
        self._lblinterface = ui.get_widget('interface')
        self._chooserxsltlabel = ui.get_widget('labelforxslt')
        self._chooserxslt = ui.get_widget('chooserforxlst')
        self._information = ui.get_widget('exportinfo')
        ui.connect_signals(signal_dict)

        self.busname = busname
        self.buspath = buspath
        self.busiface = busiface
        self.xslttype = xslttype

        self._lblbusname.set_text(busname.get_bus_name())
        self._lblobjectpath.set_text(buspath)
        self._lblinterface.set_text(busiface or '*')

        self.information = ""

        self.resultfile = None
        self.xsltfile = None
        try:
            if len(XLST_TYPES) > xslttype:
                self._chooserxsltlabel.set_text(
                    XLST_TYPES[xslttype].get('title', 'Choose one xslt file'))
                if XLST_TYPES[xslttype].has_key('file'):
                    self.xsltfile = XLST_TYPES[xslttype]['file']
                    self._chooserxslt.destroy()
                elif xslttype is XMLN:
                    self._chooserxslt.destroy()
        except Exception as e:
            print e
            self._information.set_text('Fail to open xslt, choose other.')

    def export_cb(self, obj):
        try:
            self._information.set_text('Exporting...')
            if self.has_valid_result:
                if self.xslttype is XMLN:
                    self.resultfile.write(
                        str(Dbus2Xml(
                                self.busname, #busname
                                self.buspath, #buspath
                                self.busiface or '', #bus interface
                                self.busname.get_bus()))) #bus connection
                    self._information.set_text('Exported')
                elif self.has_valid_xslt:
                    dbus2xml = Dbus2Xml(
                                self.busname.get_bus_name(), #busname
                                self.buspath, #buspath
                                self.busiface or '', #bus interface
                                self.busname.get_bus()) #bus connection
                    xml2any = Xml2Any(dbus2xml, self.xsltfile)
                    self.resultfile.write(str(xml2any))
                    self._information.set_text('Exported')
                self.resultfile.close()
                self.resultfile = None
            else:
                self._information.set_text('Cannot save result in this file')
        except Exception as e:
            print e
            self._information.set_text('Exeption when exporting')

    @property
    def has_valid_xslt(self):
        if not self.xsltfile: return False
        return True

    @property
    def has_valid_result(self):
        if not self.resultfile:
            _chooserresult = gtk.FileChooserDialog("Save File...", self.dialog,
                                        gtk.FILE_CHOOSER_ACTION_SAVE,
                                        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                         gtk.STOCK_SAVE, gtk.RESPONSE_OK))
            result = _chooserresult.run()
            if result == gtk.RESPONSE_OK:
                self.resultfile = open(_chooserresult.get_filename(), 'w')
            _chooserresult.destroy()
        if not isinstance(self.resultfile, file): return False
        return True


    def choose_file_Cb(self, obj, *args, **kws):
        self.xsltfile = obj.get_file().read()

    @property
    def information(self):
        return self._information.get_text()

    @information.setter
    def information(self, text):
        self._information.set_text(text)

    def run(self):
        self.dialog.run()

    def close_cb(self, *args, **kws):
        self.dialog.destroy()


    @staticmethod
    def get_menu_item(label, busname, buspath,
                      busiface=None, xsltype=0):
        item = gtk.MenuItem(label)

        def callback(*args, **kws):
            return ExportInterfaceDialog(busname,
                                         buspath,
                                         busiface,
                                         xsltype).run()

        item.connect('activate', callback)
        item.show()
        return item

    @staticmethod
    def get_node_menuitems(busname, buspath, busiface=None):
        if isinstance(busname, (list, tuple)): busname = busname[0]
        if isinstance(buspath, (list, tuple)): buspath = buspath[0]
        if isinstance(busiface, (list, tuple)): busiface = busiface[0]
        items = []
        for i in range(LEN_XLST_TYPES):
                items.append(ExportInterfaceDialog.get_menu_item(
                XLST_TYPES[i]['name'],
                busname,
                buspath,
                busiface, i))
        return items
