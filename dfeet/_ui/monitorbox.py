from uiloader import UILoader
from dfeet.dbus_monitor import DbusMonitor
import gtk, gobject

class MonitorBox(gtk.VBox):
    __gsignals__ = {
        'started': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,)),
        'stoped': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,)),
    }
    def __init__(self, busname, dbusmonitor, *args, **kw):
        signal_dict = {
                        'destroy_monitor_box_cb' : self.stop,
                      }
        gtk.VBox.__init__(self)
        self.connect('destroy', self.stop)
        self.ui = UILoader(UILoader.UI_MONITORBOX)

        self.root_widget = self.ui.get_root_widget()

        self.busname = busname
        self.dbusmonitor = dbusmonitor

        self.ui.connect_signals(signal_dict)

        self.textviews = {
             DbusMonitor.MSG_ERROR: 'errostextview',
             DbusMonitor.MSG_METHOD: 'calltextview',
             DbusMonitor.MSG_RETURN: 'resulttextview',
             DbusMonitor.MSG_SIGNAL: 'signalstextview',
        }

        self.callback = None

        self.root_widget.show_all()
        self.add(self.ui.get_root_widget())
        self.show_all()


    #callback
    def monitore(self, bus, message, dbusmonitor, *args, **kws):
        print 'rule: ', dbusmonitor.rule
        print DbusMonitor.message_printer(message)
        mtype = message.get_type()
        if mtype in self.textviews.keys():
            self.ui.get_widget(self.textviews.get(mtype))\
                .get_buffer().insert_at_cursor(DbusMonitor.message_printer(message))

    def start(self, *args, **kws):
        def  _filter_cb(bus, message, dbusmonitor, * args, **kws):
            return self.monitore(bus, message, dbusmonitor, *args, **kws)
        self.callback = _filter_cb
        self.dbusmonitor.start(_filter_cb)
        self.emit('started', self.dbusmonitor)

    def stop(self, *args, **kws):
        if self.callback:
            self.dbusmonitor.stop()
            self.callback = None
        self.emit('stoped', self.dbusmonitor)

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


