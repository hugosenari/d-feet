from uiloader import UILoader
from dfeet.dbus_monitor import DbusMonitor
from gi.repository import Gtk, Gio, GLib

class MonitorBox(Gtk.VBox):
    """Class to handle dbus monitor interface"""

    def __del__(self):
        try:
            self.stop()
        except:
            pass
        
    def __exit__(self):
        self.__del__()
        
    def __init__(self, busname, dbusmonitor, data_dir, *args, **kw):
        self.busname = busname
        self.dbusmonitor = dbusmonitor
        self.callback = None
        self.data_dir = data_dir
        self.ui = UILoader(data_dir, UILoader.UI_MONITORBOX)
        self.root_widget = self.ui.get_root_widget()
        
        self.__init_gtk()

    def __init_gtk(self):
        Gtk.VBox.__init__(self)      
        self.connect('destroy', self.stop)
        self.add(self.ui.get_root_widget())       
        self.root_widget.show_all()
        self.show_all()

    #callback
    def register_message(self, bus, message, dbusmonitor, *args, **kws):
        textview = self.ui.get_widget('monitortextview')
        formated_msg = DbusMonitor.message_printer(message)
        text_buffer = textview.get_buffer()
        text_buffer.insert_at_cursor(formated_msg)

    def start(self, *args, **kws):
        def  _filter_cb(bus, message, dbusmonitor, * args, **kws):
            return self.register_message(bus, message, dbusmonitor, *args, **kws)
        self.callback = _filter_cb
        self.dbusmonitor.start(_filter_cb)
    
    def stop(self, *args, **kws):
        if self.callback:
            self.dbusmonitor.stop()
            self.callback = None

    #constructor helpers
    @staticmethod
    def new_with_monitor(busname,
        sender=None, path=None, interface=None, mtype=None, member=None,
        *args, **kws):
        '''
        Create one new MonitorBox
        with parameters:
            sender: busname of who are sending message
            path: object path of who are sending message
            interface: dbus interface
            mtype: type of member, one of:
                MonitorDialog.MSG_ERROR for error messages only
                MonitorDialog.MSG_SINGAL for signal messages only
                MonitorDialog.MSG_METHOD for method call messages only
                MonitorDialog.MSG_RETURN for method return messages only
            member: member to be watched (name of method or signal)
            more args are converted in filter
            see:
            http://dbus.freedesktop.org/doc/dbus-specification.html#message-bus-routing-match-rules
        '''
        return MonitorBox(busname,
            sender=sender, path=path, interface=interface, mtype=mtype, member=member,
            *args, **kws)
