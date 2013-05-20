import gtk
import _ui

from . import dbus_introspector
from . import introspect_data

from .dbus_introspector import BusWatch
from .settings import Settings
from ._ui.uiloader import UILoader
from ._ui.addconnectiondialog import AddConnectionDialog
from ._ui.executemethoddialog import ExecuteMethodDialog


class DFeetApp:

    HISTORY_MAX_SIZE = 10

    def __init__(self):
        signal_dict = {'add_session_bus': self.add_session_bus_cb,
                       'add_system_bus': self.add_system_bus_cb,
                       'add_bus_address': self.add_bus_address_cb,
                       'reconnect_current_bus': self.reconnect_current_bus_cb,
                       'execute_method': self.execute_current_method_cb,
                       'quit': self.quit_cb}

        self.ICON_SIZE_CLOSE_BUTTON = gtk.icon_size_register(
            'ICON_SIZE_CLOSE_BUTTON', 14, 14)

        settings = Settings.get_instance()

        ui = UILoader(UILoader.UI_MAINWINDOW)

        self.main_window = ui.get_root_widget()
        self.main_window.set_icon_name('dfeet-icon')
        self.main_window.connect('delete-event', self._quit_dfeet)

        self.notebook = ui.get_widget('display_notebook')
        self.notebook.show_all()

        self.execute_method_action = ui.get_widget('execute_method')
        self.reconnect_current_bus_action = ui.get_widget(
            'reconnect_current_bus')

        self.notebook.connect('switch-page', self.switch_tab_cb)

        self.main_window.set_default_size(int(settings.general['windowwidth']),
                                 int(settings.general['windowheight']))

        self._load_tabs(settings)
        self._load_addbus_history(settings)

        self.main_window.show()

        ui.connect_signals(signal_dict)

    def _load_tabs(self, settings):
        for bus_name in settings.general['bustabs_list']:
            if bus_name == 'Session Bus':
                self.add_bus(dbus_introspector.SESSION_BUS)
            elif bus_name == 'System Bus':
                self.add_bus(dbus_introspector.SYSTEM_BUS)
            else:
                self.add_bus(address=bus_name)

    def _load_addbus_history(self, settings):
        self.add_bus_history = []
        self.combo_addbus_history_model = gtk.ListStore(str)
        for bus_add in settings.general['addbus_list']:
            if bus_add != '':
                self.add_bus_history.append(bus_add)

    def _add_bus_tab(self, bus_watch, position=None):
        name = bus_watch.get_bus_name()
        bus_paned = _ui.BusBox(bus_watch)
        bus_paned.connect('introspectnode-selected',
                          self.introspect_node_selected_cb)
        bus_paned.show_all()
        hbox = gtk.HBox()
        hbox.pack_start(gtk.Label(name), True, True)
        close_btn = gtk.Button()
        img = gtk.Image()
        img.set_from_stock(gtk.STOCK_CLOSE, self.ICON_SIZE_CLOSE_BUTTON)
        img.show()
        close_btn.set_image(img)
        close_btn.set_relief(gtk.RELIEF_NONE)
        close_btn.connect('clicked', self.close_tab_cb, bus_paned)
        hbox.pack_start(close_btn, False, False)
        hbox.show_all()

        if position:
            self.notebook.insert_page(bus_paned, hbox, position)
            self.notebook.set_current_page(position)
            self.notebook.set_tab_reorderable(bus_paned, True)
        else:
            p = self.notebook.append_page(bus_paned, hbox)
            self.notebook.set_current_page(p)
            self.notebook.set_tab_reorderable(bus_paned, True)

    def introspect_node_selected_cb(self, widget, node):
        if isinstance(node, introspect_data.Method):
            self.execute_method_action.set_sensitive(True)
        else:
            self.execute_method_action.set_sensitive(False)

    def execute_current_method_cb(self, action):
        page = self.notebook.get_current_page()
        if page >= 0:
            busbox = self.notebook.get_nth_page(page)
            node = busbox.get_selected_introspect_node()
            busname = busbox.get_selected_busname()
            dialog = ExecuteMethodDialog(busname, node)
            dialog.run()

    def close_tab_cb(self, button, child):
        n = self.notebook.page_num(child)
        if child.get_bus_watch().get_bus_name() not in\
            ['Session Bus', 'System Bus']:
            child.get_bus_watch().close_bus()
        self.notebook.remove_page(n)
        if self.notebook.get_n_pages() <= 0:
            self.reconnect_current_bus_action.set_sensitive(False)

    def switch_tab_cb(self, notebook, page, page_num):
        child = self.notebook.get_nth_page(page_num)
        if child.get_bus_watch().get_bus_name() not in\
            ['Session Bus', 'System Bus']:
            self.reconnect_current_bus_action.set_sensitive(True)
        else:
            self.reconnect_current_bus_action.set_sensitive(False)

    def select_or_add_bus(self, address):
        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            tab_label = self.notebook.get_tab_label(page)
            if tab_label.get_children()[0].get_text() == address:
                self.notebook.set_current_page(i)
                break
        else:
            self.add_bus(address=address)

    def add_bus(self, bus_type=None, address=None):
        if bus_type == dbus_introspector.SESSION_BUS or\
            bus_type == dbus_introspector.SYSTEM_BUS:
            bus_watch = BusWatch(bus_type)
            self._add_bus_tab(bus_watch)
        else:
            try:
                bus_watch = BusWatch(None, address=address)
                self._add_bus_tab(bus_watch)
            except Exception as e:
                print(e)

    def add_session_bus_cb(self, action):
        self.add_bus(dbus_introspector.SESSION_BUS)

    def add_system_bus_cb(self, action):
        self.add_bus(dbus_introspector.SYSTEM_BUS)

    def add_bus_address_cb(self, action):
        dialog = AddConnectionDialog(self.main_window)
        self.combo_addbus_history_model.clear()
        # Load combo box history
        for el in self.add_bus_history:
            self.combo_addbus_history_model.append([el])
        dialog.set_model(self.combo_addbus_history_model)
        result = dialog.run()
        if result == 1:
            bus_address = dialog.get_address()
            if bus_address == 'Session Bus':
                self.add_bus(dbus_introspector.SESSION_BUS)
            elif bus_address == 'System Bus':
                self.add_bus(dbus_introspector.SYSTEM_BUS)
            else:
                self.add_bus(address=bus_address)
                # Fill history
                if bus_address in self.add_bus_history:
                    self.add_bus_history.remove(bus_address)
                self.add_bus_history.insert(0, bus_address)
                # Truncating history
                if (len(self.add_bus_history) > self.HISTORY_MAX_SIZE):
                    self.add_bus_history = \
                        self.add_bus_history[0:self.HISTORY_MAX_SIZE]

        dialog.destroy()

    def reconnect_current_bus_cb(self, action):
        page = self.notebook.get_current_page()
        if page >= 0:
            child = self.notebook.get_nth_page(page)
            bus_watch = child.get_bus_watch()

            bus_type = bus_watch.get_bus_type()
            bus_address = bus_watch.get_bus_address()

            if bus_type == dbus_introspector.SESSION_BUS or\
                bus_type == dbus_introspector.SYSTEM_BUS:
                pass
            else:
                bus_watch.close_bus()
                self.notebook.remove_page(page)
                try:
                    new_bus_watch = BusWatch(None, address=bus_address)
                    self._add_bus_tab(new_bus_watch, page)
                except Exception as e:
                    print(e)

    def quit_cb(self, action):
        self._quit_dfeet(self.main_window, None)

    def _quit_dfeet(self, main_window, event):
        settings = Settings.get_instance()
        size = main_window.get_size()
        ## pos = main_window.get_position()

        settings.general['windowwidth'] = size[0]
        settings.general['windowheight'] = size[1]

        n = self.notebook.get_n_pages()
        tab_list = []
        for i in range(n):
            child = self.notebook.get_nth_page(i)
            bus_watch = child.get_bus_watch()
            tab_list.append(bus_watch.get_bus_name())

        self.add_bus_history = self.add_bus_history[0:self.HISTORY_MAX_SIZE]

        settings.general['bustabs_list'] = tab_list
        settings.general['addbus_list'] = self.add_bus_history

        settings.write()

        gtk.main_quit()

if __name__ == "__main__":
    DFeetApp()
    gtk.main()
