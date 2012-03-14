import gobject 
import gtk
import pango 

from dfeet import _util
from dfeet.introspect_data import IntrospectData, Method, Signal, ObjectPath, Interface

from executemethoddialog import ExecuteMethodDialog
from exportbusdialog import ExportInterfaceDialog
from uiloader import UILoader

class BusNameInfoBox(gtk.VBox):
    __gsignals__ =  {
        'selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT,))
    }

    def __init__(self):
        super(BusNameInfoBox, self).__init__()

        self.busname = None

        ui = UILoader(UILoader.UI_INTROSPECTVIEW) 
        info_table = ui.get_root_widget()
        self.name_label = ui.get_widget('name_label1')
        self.unique_name_label = ui.get_widget('unique_name_label1')
        self.process_label = ui.get_widget('process_label1')
        self.introspection_box = ui.get_widget('introspect_box1')

        self.introspect_tree_view = gtk.TreeView()

        button_renderer = gtk.CellRendererPixbuf()
        text_renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Introspection Data", 
                                    None)

        column.pack_start(button_renderer, False)
        column.pack_start(text_renderer, True)

        column.add_attribute(button_renderer, 'icon-name', 
                             IntrospectData.ICON_NAME_COL)
        column.add_attribute(text_renderer, 'markup', 
                             IntrospectData.DISPLAY_COL)

        column.set_cell_data_func(text_renderer, 
                                  self.text_cell_data_handler, 
                                  self.introspect_tree_view)

        self.introspect_tree_view.connect('row-collapsed', 
                                          self.row_collapsed_handler)
        self.introspect_tree_view.connect('row-expanded', 
                                          self.row_expanded_handler)
        self.introspect_tree_view.connect('cursor-changed',
                                          self.cursor_changed_handler)

        self.introspect_tree_view.append_column(column) 
        
        scroll = gtk.ScrolledWindow()
        scroll.add(self.introspect_tree_view)
        self.introspection_box.pack_start(scroll,
                                          True, True)

        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.introspect_tree_view.show_all()

        self.add(info_table)

        self.introspect_tree_view.connect('row-activated', 
                                          self.row_activated_handler)

        #context menu
        self.menu = None
        self.introspect_tree_view.connect('button-press-event', self.right_click_only)

    def right_click_only(self, treeview, event):
        if event.button == 3: #3 = right click
            pthinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
            if pthinfo:
                self.row_menu_activated_handler(treeview, pthinfo[0], event)

    def row_menu_activated_handler(self, treeview, path, event):
        model = treeview.get_model()
        iter = model.get_iter(path)
        node = model.get_value(iter, IntrospectData.SUBTREE_COL)
        #we can export all objectpath or only one interface
        if isinstance(node, (ObjectPath, Interface)):
            busiface = None
            if isinstance(node, Interface):
                busiface = node.iface
                while not isinstance(node, ObjectPath):
                    node = node.parent

            buspath = node.path

            items = ExportInterfaceDialog\
                .get_node_menuitems(
                                    self.busname.get_display_name(),
                                    buspath, busiface)
            if len(items):
                if self.menu: self.menu.destroy()
                self.menu = gtk.Menu()
                for item in items:
                    self.menu.append(item)
                self.menu.popup(None, None, None, event.button, event.time)

    def row_activated_handler(self, treeview, path, view_column):
        model = treeview.get_model() 
        iter = model.get_iter(path)

        node = model.get_value(iter, IntrospectData.SUBTREE_COL)

        if isinstance(node, Method):
            dialog = ExecuteMethodDialog(self.busname, node)
            dialog.run()
        else:
            if treeview.row_expanded(path):
                treeview.collapse_row(path)
            else:
                treeview.expand_row(path, False)

    def row_collapsed_handler(self, treeview, iter, path):
        model = treeview.get_model()
        node = model.get(iter, model.SUBTREE_COL)[0]
        node.set_expanded(False)

    def row_expanded_handler(self, treeview, iter, path):
        model = treeview.get_model()
        node = model.get(iter, model.SUBTREE_COL)[0]
        node.set_expanded(True)

    def cursor_changed_handler(self, treeview):
        node = self.get_selected_node()
        if node:
            node.on_selected(self.busname)
            self.emit('selected', node)

    def get_selected_node(self):
        selection = self.introspect_tree_view.get_selection()
        model, iter = selection.get_selected()
        if not iter:
            return None 
             
        node = model.get(iter, model.SUBTREE_COL)[0]
        return node

    def text_cell_data_handler(self, column, cell, model, iter, treeview):
        node = model.get(iter, model.SUBTREE_COL)[0]
        if node.is_expanded():
            path = model.get_path(iter)
            treeview.expand_row(path, False)

    def introspect_changed(self, busname):
        #print busname.common_data._introspection_data
        pass

    def set_busname(self, busname):
        if self.busname:
            try:
                self.busname.disconnect(self.busname._introspect_changed_signal_id)
            except:
                pass

        self.busname = busname
        self.introspect_tree_view.set_model(busname.common_data._introspection_data)
        if self.busname:
            self.busname.query_introspect()
            self.busname._introspect_changed_signal_id = self.busname.connect('changed', self.introspect_changed)

        self.refresh()

    def clear(self):
        self.busname = None
        self.refresh()

    def refresh(self):
        name = ''
        unique_name = ''
        process_path_str = ''

        if self.busname:
            name = self.busname.get_display_name()
            unique_name = self.busname.get_unique_name()
            process_path = self.busname.get_process_path()
            process_path_str = ""
            if not process_path:
                process_path_str = 'Unknown or Remote: This process can not be found and may be remote'
            else:
                process_path_str = ' '.join(process_path)

        self.name_label.set_text(name)
        self.unique_name_label.set_text(unique_name)
        self.process_label.set_text(process_path_str)
