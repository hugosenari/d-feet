from dfeet.dbus_utils import sig_to_string
from dbus import lowlevel
from dfeet.introspect_data import Method, Signal, Property, \
MethodLabel, SignalLabel, PropertyLabel, \
Interface, ObjectPath, \
InterfaceLabel, ObjectPathLabel, \
LeafNode
from blueman.main.DbusService import DbusService

class DbusMonitor(object):
    MSG_ERROR = lowlevel.MESSAGE_TYPE_ERROR
    MSG_METHOD = lowlevel.MESSAGE_TYPE_METHOD_CALL
    MSG_RETURN = lowlevel.MESSAGE_TYPE_METHOD_RETURN
    MSG_SIGNAL = lowlevel.MESSAGE_TYPE_SIGNAL
    MESSAGE_TYPES = {
                 lowlevel.MESSAGE_TYPE_ERROR: 'error',
                 lowlevel.MESSAGE_TYPE_METHOD_CALL: 'method_call',
                 lowlevel.MESSAGE_TYPE_METHOD_RETURN: 'method_return',
                 lowlevel.MESSAGE_TYPE_SIGNAL: 'signal'
    }
    '''
    Monitore informations passing over one bus
    '''
    def __init__(self,
                 #class params
                 busname,
                 #filter params
                 sender=None, path=None, interface=None, mtype=None, member=None, destination=None,
                 #more filter parms
                 * args, **kws):
        '''
        busname: dfeet.dbus_introspector.BusName
        sender: busname of who are sending message
        path: object path of who are sending message
        interface: dbus interface
        mtype: type of member, one of:
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
        self.con = busname.get_bus()

        self.callback = None
        self._filter_cb = None

        self.type = mtype
        self.rule = ''
        self.state = 0

        kws.update({
            'sender': sender,
            'path': path,
            'interface': interface,
            'member': member,
            'destination': destination,
        })
        for attr in kws.keys():
            setattr(self, attr, kws[attr])
        self.filters = kws

    def start(self, callback=None, *args, **kws):
        if self._filter_cb:
            self.stop()
        self.callback = callback
        #first we convert parms to rule
        self.rule = ''
        if self.type and \
            self.type in self.__class__.MESSAGE_TYPES.keys():
            self.rule = self.rule + "type='%s'," % (self.__class__.MESSAGE_TYPES.get(self.type))
        for filter in self.filters.keys():
            if self.filters[filter]:
                self.rule = self.rule + "%s='%s'," % (filter, self.filters[filter])
        #remove last ,
        self.rule = self.rule[0:-1]
        print self.rule, self.__class__

        #define rules and callback 
        def  _filter_cb(bus, message, *args, **kws):
            try:
                return self.message_filter(bus, message, *args, **kws)
            except Exception as e:
                print e
            return lowlevel.HANDLER_RESULT_NOT_YET_HANDLED
        self._filter_cb = _filter_cb
        self.con.add_match_string(self.rule)
        self.con.add_message_filter(self._filter_cb)


    def stop(self, *args, **kws):
        try:
            self.con.remove_match_string(self.rule)
            self.con.remove_message_filter(self._filter_cb)
            self._filter_cb = None
        except Exception as e:
            print e

    def message_filter(self, bus, message, *args, **kws):
        try:
            if self.callback:
                getattr(self, 'callback')(bus, message, self)
        except Exception as e:
            print e
        return lowlevel.HANDLER_RESULT_NOT_YET_HANDLED

    @staticmethod
    def message_printer(message=None, *args, **kw):
        if message:
            return \
                "\nmessage type: %s : %s\n" % (message.get_type(), message.__class__) + \
                "from: %s::%s::%s::%s\n" % (
                    message.get_sender() or '',
                    message.get_path() or '',
                    message.get_interface() or '',
                    message.get_member() or '') + \
                "to: %s \n" % (message.get_destination() or '') + \
                "signature: %s \n" % (message.get_signature() or '') + \
                "content: %s \n" % (message.get_args_list()  or '') + \
                (("error: %s \n" % message.get_error_name()) if message.get_error_name() else "")
        return ''

    @staticmethod
    def get_rule_for_node(node):
        '''
        Return dict to call DbusMonitor(**rule) 
        This version use only one information of node to create rule
        Use get_rules_for_node for more especific rule 
        '''
        return node.get_rule()

    @staticmethod
    def get_rules_for_node(node):
        '''
        Return dict to call DbusMonitor(**rule)
        This version use all information of node to create rule
        Use ger_rule_for_node for more generic rule
        '''
        result = {}
        while node.parent:
            result.update(node.get_rule())
            node = node.parent
        return result

    @staticmethod
    def get_from_for_busname(busname):
        '''
        Return dict to call DbusMonitor(**rule)
        This rule match who send message 
        '''
        return {'sender': busname.get_display_name()}

    @staticmethod
    def get_to_for_busname(busname):
        '''
        Return dict to call DbusMonitor(**rule)
        This rule match who receive message
        '''
        return {'destination': busname.get_unique_name()}

    @property
    def is_group(self):
        return False


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

class SenderMonitor(DbusMonitor):
    '''
    Use in cases where introspected bus will be sender of messege
    busname: dfeet.dbus_introspector.BusName
    sender: str, bus name of sender
    member: str, member to be watched (name of method or signal)
    '''
    def __init__(self, busname, sender=None, member=None, *args, **kws):
        DbusMonitor.__init__(self,
                busname,
                sender=sender or busname.get_unique_name(),
                member=member, *args, **kws)


class DestinationMonitor(DbusMonitor):
    '''
    Use in case where introspected bus will be destination of message
    busname: dfeet.dbus_introspector.BusName
    member: str, member to be watched (name of method or signal)
    destination: str, busname of destination
    '''
    def __init__(self, busname, member=None, destination=None, *args, **kws):
        DbusMonitor.__init__(self,
                busname, member=member,
                destination=destination or busname.get_unique_name(),
                *args, **kws)


class SignalMonitor(SenderMonitor):
    '''
    Signal of introspected interface
    busname: dfeet.dbus_introspector.BusName
    member: str, member to be watched (name of signal) 
    '''
    def __init__(self, busname, member=None, *args, **kws):
        SenderMonitor.__init__(
            self, busname,
            mtype=kws.get('mtype', DbusMonitor.MSG_SIGNAL),
            member=member, *args, **kws)


class CallMonitor(DestinationMonitor):
    '''
    Method call in instrospected interface 
    busname: dfeet.dbus_introspector.BusName
    member: str, member to be watched (name of method) 
    destination: str, that will be descarted
    '''
    def __init__(self, busname, member=None, *args, **kws):
        DestinationMonitor.__init__(
            self, busname,
            mtype=kws.get('mtype', DbusMonitor.MSG_METHOD),
            member=member,
            *args, **kws)


class ReturnMonitor(SenderMonitor):
    '''
    Method return of introspected interface
    busname: dfeet.dbus_introspector.BusName
    member: str, member to be watched (name of method)
    '''
    def __init__(self, busname, member=None, *args, **kws):
        SenderMonitor.__init__(
            self, busname,
            mtype=kws.get('mtype', DbusMonitor.MSG_RETURN),
            member=member, *args, **kws)


class ErrorMonitor(SenderMonitor):
    '''
    Error return of introspected interface
    busname: dfeet.dbus_introspector.BusName
    '''
    def __init__(self, busname, *args, **kws):
        SenderMonitor.__init__(
            self, busname,
            mtype=kws.get('mtype', DbusMonitor.MSG_ERROR),
            *args, **kws)


class MethodMonitor(DbusMonitors):
    '''
    Method group: (Method Call and Method Result 
    busname: dfeet.dbus_introspector.BusName
    member: str, member to be watched (name of method)
    '''
    def __init__(self, busname, member=None, *args, **kws):
        DbusMonitors.__init__(self, [
            CallMonitor(busname, member=member, *args, **kws),
            ReturnMonitor(busname, member=member, *args, **kws)
        ], *args, **kws)

class InterfaceMonitor(DbusMonitors):
    '''
    Interface group
    '''
    def __init__(self, busname, interface=None, *args, **kws):
        DbusMonitors.__init__(self,
            [MethodMonitor(busname, interface=interface, *args, **kws),
            ErrorMonitor(busname, interface=interface, *args, **kws),
            SignalMonitor(busname, interface=interface, *args, **kws)
        ], *args, **kws
        )

class PathMonitor(DbusMonitors):
    '''
    Object Path group
    '''
    def __init__(self, busname, path=None, *args, **kws):
        DbusMonitors.__init__(self, [
            MethodMonitor(busname, path=path, *args, **kws),
            ErrorMonitor(busname, path=path, *args, **kws),
            SignalMonitor(busname, path=path, *args, **kws)
        ], *args, **kws
        )

class DbusName(DbusMonitors):
    '''
    Object DbusName group
    '''
    def __init__(self, busname, *args, **kws):
        DbusMonitors.__init__(self, [
            MethodMonitor(busname, *args, **kws),
            ErrorMonitor(busname, *args, **kws),
            SignalMonitor(busname, *args, **kws)
        ], *args, **kws
        )


NODE_TO_MONITOR = {
    Signal : SignalMonitor,
    Method : MethodMonitor,
    Property : MethodMonitor,
    MethodLabel : InterfaceMonitor,
    SignalLabel : InterfaceMonitor,
    PropertyLabel : InterfaceMonitor,
    Interface : InterfaceMonitor,
    InterfaceLabel : PathMonitor,
    ObjectPath : PathMonitor,
    ObjectPathLabel : DbusName,
}

def node_to_monitor(node):
    return NODE_TO_MONITOR.get(node.__class__, DbusName)

