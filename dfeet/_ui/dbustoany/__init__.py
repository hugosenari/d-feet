#!/usr/bin/python
'''
Converts dbus to any using xslt

Created on Jan 5, 2012

@author: hugosenari
'''

import re
import dbus
import libxslt
import libxml2
from libxml2 import xmlDoc

def replace(ctx, string, pattern, repl, *args, **kwargs):
    return re.sub(pattern, repl, string)

def lower_case(ctx, string, *args, **kwargs):
    return string.lower()

libxslt.registerExtModuleFunction("replace", "https://github.com/hugosenari", replace)
libxslt.registerExtModuleFunction("lower-case", "https://github.com/hugosenari", lower_case)

class XmlHelper(object):
    '''
    Class with utilities
    '''

    @staticmethod
    def toXmlDoc(xml, *args, **kwargs):
        '''
        Converts xml file path or xml str in libxml2.xmlDoc
        '''
        #test if is xmldoc
        if isinstance(xml, xmlDoc):
            return xml
        #test if is readable
        elif hasattr(xml, "file"):
            return libxml2.parseFile(xml.file)
        #test if is readable
        elif hasattr(xml, "read"):
            _xml = xml.read()
            return libxml2.parseDoc(_xml)
        #test if has tag
        else:
            _xml = str(xml).strip()
            if re.findall("<[!a-zA-Z]+", _xml, re.MULTILINE):
                return libxml2.parseDoc(_xml)
            #try to open string as file
            else:
                return libxml2.parseFile(_xml)
        return xml

    @staticmethod
    def xmlTo(xml, xslt, *args, **kwargs):
        '''
        Converts xml to anything defined by xslt
        Keywords was passed to stylesheet as param
        '''
        xsl = libxslt.parseStylesheetDoc(xslt)
        result = xsl.applyStylesheet(xml, kwargs)
        xsl.freeStylesheet()
        return result

    @staticmethod
    def freeDoc(*args):
        pass
#        for arg in args:
#            arg.freeDoc()

class Dbus2Xml(object):
    '''
    Get information from dbus introspection
    '''

    def __init__(self, bus_name, object_path, interface='', bus=None, obj=None, *args, **kwargs):
        '''
        Contructor
        '''
        self.bus = bus or dbus.SessionBus.get_session()
        self.obj = obj or self.bus.get_object(bus_name, object_path)
        method = self.obj.get_dbus_method("Introspect", dbus_interface="org.freedesktop.DBus.Introspectable")
        self._xml = method()
        self.bus_name = bus_name
        self.obj_path = object_path
        self.interface = interface

    @property
    def xml(self, *args, **kwargs):
        return XmlHelper.toXmlDoc(self._xml, *args, **kwargs)

    @property
    def content(self):
        return self.xml.content

    def __str__(self, *args, **kwargs):
        return str(self._xml)

class Xml2Any(object):
    '''
    Convert xml string to anything defined by some xslt
    '''
    def __init__(self, xml, xslt, *args, **kwargs):
        self._xml = XmlHelper.toXmlDoc(xml, *args, **kwargs) if not hasattr(xml, "xml")\
            else xml.xml
        self._kwargs = {
              'bus_name' : str("'" + getattr(xml, 'bus_name', "") + "'"),
              'object_path' : str("'" + getattr(xml, 'obj_path', "") + "'"),
              'interface' : str("'" + getattr(xml, 'interface', "") + "'"),
        }
        self._args = args
        self._kwargs.update(kwargs)
        self._xslt = xslt

    def convert(self, *args, **kwargs):
        ar = []
        ar.extend(args)
        ar.extend(self._args)
        kw = self._kwargs
        kw.update(kwargs)
        xml = self.xml
        xslt = self.xslt
        result = XmlHelper.xmlTo(xml, xslt, *ar, **kw)
        XmlHelper.freeDoc(xslt, xml)
        return result

    @property
    def xml(self, *args, **kwargs):
        return XmlHelper.toXmlDoc(self._xml, *args, **kwargs)

    @property
    def xslt(self, *args, **kwargs):
        return XmlHelper.toXmlDoc(self._xslt, *args, **kwargs)

    @property
    def content(self):
        return self.convert()

    def __str__(self, *args, **kwargs):
        doc = self.convert(*args, **kwargs)
        result = doc.content if doc and hasattr(doc, "content") else ""
        XmlHelper.freeDoc(doc)
        return result



if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Convert dbus interfaces xml in code', prog='dbustoany')
    parser.add_argument('xslt', type=str,
                       help='xslt stylesheet path')
    parser.add_argument('busName', type=str,
                       help='dbus name for object that you want convert')
    parser.add_argument('objectPath', type=str,
                       help='dbus object path for object that you want convert')
#    parser.add_argument('--interface', '-i', metavar='interface', type=str,
#                       help='interface if you want show to especific interface')
#    parser.add_argument('--xml', '-x', metavar='xml', type=str,
#                       help='xml path of dbus object interfaces')

    args = parser.parse_args()
    dbus2xml = Dbus2Xml(args.busName, args.objectPath)

    xml2any = Xml2Any(dbus2xml, args.xslt)
    print xml2any

