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
        if path: kws['path'] = path
        if sender: kws['sender'] = sender
        if member: kws['member'] = member
        if interface: kws['interface'] = interface
        if destination: kws['destination'] = destination
        
        self.busname = busname
        self.con = connection
        self.callback = None
        self._filter_cb = None
        self.rule = ''
        self.type = msg_type
        self.state = 0
        self.filter_guid = None
        self.filters = kws
        self.proxy = None
    
    def create_proxy(self):
        self.proxy = Gio.DBusProxy.new_sync(
            self.con, #cpmmectopm
            Gio.DBusProxyFlags.NONE,
            None, #DBusInterfaceInfo
            "org.freedesktop.DBus", #name
            "/", #path
            "org.freedesktop.DBus", #iface
            None
        )
    
    def params_to_dbus_rule(self):
        self.rule = ''
        if self.type and \
            self.type in self.__class__.MESSAGE_TYPES.keys():
            self.rule = self.rule + "type=%s," % (
                self.__class__.MESSAGE_TYPES.get(self.type))
        for filter_name in self.filters.keys():
            self.rule = self.rule + "%s=%s," % (
                filter_name, self.filters[filter_name])
        #remove last ,
        self.rule = self.rule.strip(',')
        return self.rule
    
    def start(self, callback=None, *args, **kws):
        self.create_proxy()
        self.callback = callback 
        self.add_match()
        self.add_filter()
    
    def add_match(self):
        def error_handler(*args, **kwds):
            pass
        rule = self.params_to_dbus_rule()

        try:
            if self.proxy:
                self.proxy.AddMatch('(s)', rule, #signature, value
                    error_handler=error_handler)
        except:
            print("Could not set matching rule")
    
    def add_filter(self):
        def filter_cb(bus, message, b, self, *args, **kws):
            self.message_filter(bus, message, *args, **kws)
            return message
        try:
            self.filter_guid = self.con.add_filter(filter_cb, self)
        except:
            print("Could not set matching callback")
    
    def stop(self, *args, **kws):
        self.remove_filter()
        self.remove_match()
    
    def remove_match(self):
        try:
            if self.proxy:
                self.proxy.RemoveMatch('(s)', self.rule)
        except:
            print("Could not unset matching rule")
    
    def remove_filter(self):
        try:
            if self.con:
                self.con.remove_filter(self.filter_guid)
        except:
            print("Could not unset matching callback")

    def message_filter(self, bus, message, *args, **kws):
        r = self.filters
        if self.callback:
            if self.busname == message.get_sender() or\
               self.busname == message.get_destination():
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

    @staticmethod
    def Label():
        return 'BusName Monitor'