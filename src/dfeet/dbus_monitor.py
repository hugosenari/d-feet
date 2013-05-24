from dfeet.introspection_helper import DBusNode
from dfeet.introspection_helper import DBusInterface
from dfeet.introspection_helper import DBusProperty
from dfeet.introspection_helper import DBusSignal
from dfeet.introspection_helper import DBusMethod

from gi.repository import Gio, GLib

class NodeToMonitor(object):
    def __init__(self, *node_types):
        self.node_types = node_types
    
    def __call__(self, cls):
        for node_type in self.node_types:
            DbusMonitor.NODE_TO_MONITOR[node_type] = cls
        return cls


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

    def start(self, callback=None, *args, **kws):
        if self._filter_cb:
            self.stop()
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
        self._filter_cb = _filter_cb
        self.add_match(self.rule)
        self.filter_guid = self.con.add_filter(self._filter_cb, self)
        
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
        dbusIface = Gio.DBusProxy.new_sync(
            self.con, #cpmmectopm
            Gio.DBusProxyFlags.NONE,
            None, #DBusInterfaceInfo
            "org.freedesktop.DBus", #name
            "/", #path
            "org.freedesktop.DBus", #iface
            None
        )
        def error_handler(proxy_object, err, user_data):
            print err
        dbusIface.AddMatch('(s)', rule, #signature, value
            error_handler=error_handler)
        
    def remove_match(self, rule):
        proxy = Gio.DBusProxy.new_sync(
            self.con, #cpmmectopm
            Gio.DBusProxyFlags.NONE,
            None, #DBusInterfaceInfo
            "org.freedesktop.DBus", #name
            "/", #path
            "org.freedesktop.DBus", #iface
            None
        )
        proxy.call_sync(
            "RemoveMatch", #method name
            GLib.Variant('s', rule), #signature, value
            Gio.DBusCallFlags.NONE,
            -1, #timeout
            None,
        )

    def stop(self, *args, **kws):
        self.remove_match(self.rule)
        self.con.remove_filter(self.filter_guid)
        self._filter_cb = None

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
        return 'Generic Monitor'

    @staticmethod
    def node_to_monitor(node):
        def constructor(busname, conn):
            monitorclass = DbusMonitor.NODE_TO_MONITOR.get(node.__class__, DbusName)
            rules = {} 
            return monitorclass(busname, conn, **rules)
        return constructor

    @staticmethod
    def node_to_monitor_label(node):
        monitorclass = DbusMonitor.NODE_TO_MONITOR.get(node.__class__)
        return monitorclass.Label()


class DbusMonitors(object):
    '''
    Base class to monitors group
    monitor: list of DbusMonitor or DbusMonitors
    '''
    def __init__(self, monitors=[], *args, **kws):
        self.monitors = monitors

    def start(self, callback=None, *args, **kws):
        for m in self.monitors:
            m.start(callback=callback, *args, **kws)

    def stop(self, *args, **kws):
        for m in self.monitors:
            m.stop(*args, **kws)

    @property
    def rule(self):
        result = ''
        for m in self.monitors:
            result = result + m.rule
        return result

    @property
    def is_group(self):
        return True
    
    @staticmethod
    def Label():
        return 'Generic Monitor'


class SenderMonitor(DbusMonitor):
    '''
    Use in cases where introspected bus will be sender of messege
    sender: str, bus name of sender
    member: str, member to be watched (name of method or signal)
    '''
    def __init__(self, *args, **kws):
        kws['sender'] = kws.get('sender', args[0])
        super(SenderMonitor, self).__init__(*args, **kws)
    
    @staticmethod
    def Label():
        return 'Sender Monitor'


class DestinationMonitor(DbusMonitor):
    '''
    Use in case where introspected bus will be destination of message
    member: str, member to be watched (name of method or signal)
    destination: str, busname of destination
    '''
    def __init__(self, *args, **kws):
        kws['destination'] = kws.get('destination', args[0])
        super(DestinationMonitor, self).__init__(*args, **kws)

    @staticmethod
    def Label():
        return 'Destination Monitor'


@NodeToMonitor(DBusSignal)
class SignalMonitor(SenderMonitor):
    '''
    Signal of introspected interface
    member: str, member to be watched (name of signal) 
    '''
    def __init__(self, *args, **kws):
        kws['msg_type'] = kws.get('msg_type', DbusMonitor.MSG_SIGNAL)
        super(SignalMonitor, self).__init__(*args, **kws)

    @staticmethod
    def Label():
        return 'Signal Monitor'


class CallMonitor(DestinationMonitor):
    '''
    Method call in instrospected interface 
    member: str, member to be watched (name of method) 
    destination: str, that will be descarted
    '''
    def __init__(self, *args, **kws):
        kws['msg_type'] = kws.get('msg_type', DbusMonitor.MSG_METHOD)
        super(CallMonitor, self).__init__(*args, **kws)

    @staticmethod
    def Label():
        return 'Method Call Monitor'


class ReturnMonitor(SenderMonitor):
    '''
    Method return of introspected interface
    member: str, member to be watched (name of method)
    '''
    def __init__(self, *args, **kws):
        kws['msg_type'] = kws.get('msg_type', DbusMonitor.MSG_RETURN)
        super(ReturnMonitor, self).__init__(*args, **kws)

    @staticmethod
    def Label():
        return 'Method Return Monitor'


class ErrorMonitor(SenderMonitor):
    '''
    Error return of introspected interface
    '''
    def __init__(self, *args, **kws):
        kws['msg_type'] = kws.get('msg_type', DbusMonitor.MSG_ERROR)
        super(ErrorMonitor, self).__init__(*args, **kws)

    @staticmethod
    def Label():
        return 'Error Monitor'


@NodeToMonitor(DBusMethod, DBusProperty)
class MethodMonitor(DbusMonitors):
    '''
    Method group: (Method Call and Method Result 
    member: str, member to be watched (name of method)
    '''
    def __init__(self, *args, **kws):
        super(MethodMonitor, self).__init__([
            CallMonitor(*args, **kws),
            ReturnMonitor(*args, **kws)
        ], *args, **kws)

    @staticmethod
    def Label():
        return 'Method Monitor'


@NodeToMonitor(DBusInterface)
class InterfaceMonitor(DbusMonitors):
    '''
    Interface group
    '''
    def __init__(self, *args, **kws):
        super(InterfaceMonitor, self).__init__([
            MethodMonitor(*args, **kws),
            ErrorMonitor(*args, **kws),
            SignalMonitor(*args, **kws)
        ], *args, **kws)

    @staticmethod
    def Label():
        return 'Interface Monitor'


class PathMonitor(DbusMonitors):
    '''
    Object Path group
    '''
    def __init__(self, *args, **kws):
        super(PathMonitor, self).__init__([
            MethodMonitor(*args, **kws),
            ErrorMonitor(*args, **kws),
            SignalMonitor(*args, **kws)
        ], *args, **kws)

    @staticmethod
    def Label():
        return 'Path Monitor'


@NodeToMonitor(DBusNode)
class DbusName(DbusMonitors):
    '''
    Object DbusName group
    '''
    def __init__(self, *args, **kws):
        super(DbusName, self).__init__([
            MethodMonitor(*args, **kws),
            ErrorMonitor(*args, **kws),
            SignalMonitor(*args, **kws)
        ], *args, **kws)

    @staticmethod
    def Label():
        return 'Busname Monitor'
