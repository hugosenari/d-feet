from dfeet.introspection_helper import DBusNode
from dfeet.introspection_helper import DBusInterface
from dfeet.introspection_helper import DBusProperty
from dfeet.introspection_helper import DBusSignal
from dfeet.introspection_helper import DBusMethod

from gi.repository import Gio, GLib

class DbusMonitor(object):
    MSG_ERROR = Gio.DBusMessageType.ERROR
    MSG_METHOD = Gio.DBusMessageType.METHOD_CALL
    MSG_RETURN = Gio.DBusMessageType.METHOD_RETURN
    MSG_SIGNAL = Gio.DBusMessageType.SIGNAL
    MSG_INVALID = Gio.DBusMessageType.INVALID
    MESSAGE_TYPES = {
        MSG_ERROR: 'error',
        MSG_METHOD: 'method_call',
        MSG_RETURN: 'method_return',
        MSG_SIGNAL: 'signal',
        MSG_INVALID: 'invalid',
    }
    
    def __del__(self):
        try:
            self.stop()
        except:
            pass
        
    def __exit__(self):
        self.__del__()
    
    NODE_TO_MONITOR = {}
    '''
    Watch informations passing over one bus
    '''
    def __init__(self,
        #class params
        busname,
        connection,
        #filter params
        sender=None, path=None, interface=None,
        msg_type=None, member=None, destination=None,
        #more filter parms
        * args, **kws):
        '''
        busname: str busname
        connection: GDBusConnection
        sender: busname of who are sending message
        path: object path of who are sending message
        interface: dbus interface
        msg_type: type of member, one of:
            MonitorDialog.MSG_ERROR for error messages only
            MonitorDialog.MSG_SINGAL for signal messages only
            MonitorDialog.MSG_METHOD for method call messages only
            MonitorDialog.MSG_RETURN for method return messages only
        member: member to be watched (name of method or signal)
        destination: private busname of who are receiving message
        more args are converted in filter
        see:
        http://dbus.freedesktop.org/doc/dbus-specification.html#message-bus-routing-match-rules 
        '''
        self.con = connection

        self.callback = None
        self._filter_cb = None

        self.type = msg_type
        self.rule = ''
        self.state = 0
        self.filter_guid = None

        if sender: kws['sender'] = sender
        if path: kws['path'] = path
        if interface: kws['interface'] = interface
        if member: kws['member'] = member
        if destination: kws['destination'] = destination
        self.filters = kws
        
        self.proxy = Gio.DBusProxy.new_sync(
            self.con, #cpmmectopm
            Gio.DBusProxyFlags.NONE,
            None, #DBusInterfaceInfo
            "org.freedesktop.DBus", #name
            "/", #path
            "org.freedesktop.DBus", #iface
            None
        ) 

    def start(self, callback=None, *args, **kws):
        self.callback = callback
        #first we convert parms to rule
        self.rule = ''
        if self.type and \
            self.type in self.__class__.MESSAGE_TYPES.keys():
            self.rule = self.rule + "type=%s," % (
                self.__class__.MESSAGE_TYPES.get(self.type))
        for filter_name in self.filters.keys():
            if self.filters[filter_name]:
                self.rule = self.rule + "%s=%s," % (
                    filter_name, self.filters[filter_name])
        #remove last ,
        self.rule = self.rule.strip(',')
        #define rules and callback 
        def _filter_cb(bus, message, *args, **kws):
            slf = args[1]
            if slf.match(message): 
                slf.message_filter(bus, message, *args, **kws)
            return message
        self.add_match(self.rule)
        self.filter_guid = self.con.add_filter(_filter_cb, self)
        
    def match(self, msg):
        r = self.filters
        if msg.get_sender() == 'org.freedesktop.DBus' and\
            r.get('sender') != msg.get_sender():
            return False
        if msg.get_destination() == 'org.freedesktop.DBus' and\
            r.get('destination') != msg.get_destination():
            return False
        return True

    def add_match(self, rule):
        def error_handler(proxy_object, err, user_data):
            pass
        self.proxy.AddMatch('(s)', rule, #signature, value
            error_handler=error_handler)
        
    def remove_match(self, rule):
        self.proxy.RemoveMatch('(s)', rule)

    def stop(self, *args, **kws):
        self.remove_match(self.rule)
        self.con.remove_filter(self.filter_guid)

    def message_filter(self, bus, message, *args, **kws):
        if self.callback:
            self.callback(bus, message, self)
        return message

    @staticmethod
    def message_printer(message=None, *args, **kw):
        if message:
            return \
                "\nmessage type: %s\n" % (message.get_message_type(),) + \
                "from: %s, %s, %s, %s\n" % (
                    message.get_sender() or '',
                    message.get_path() or '',
                    message.get_interface() or '',
                    message.get_member() or '') + \
                "to: %s \n" % (message.get_destination() or '') + \
                "signature: %s \n" % (message.get_signature() or '') + \
                "content: %s \n" % (message.get_body()  or '') + \
                (("error: %s \n" % message.get_error_name()) if message.get_error_name() else "")
        return ''

    @property
    def is_group(self):
        return False
    
    @staticmethod
    def Label():
        return 'BusName Monitor'

    @staticmethod
    def node_to_monitor(node):
        def constructor(busname, conn):
            monitorclass = DbusMonitor.NODE_TO_MONITOR.get(node.__class__, DbusMonitor)
            rules = {} 
            return monitorclass(busname, conn, **rules)
        return constructor

    @staticmethod
    def node_to_monitor_label(node):
        monitorclass = DbusMonitor.NODE_TO_MONITOR.get(node.__class__, DbusMonitor)
        return monitorclass.Label()