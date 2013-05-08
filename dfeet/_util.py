import os

# TODO: Check against other Unix's
def get_proc_from_pid(pid):
    procpath = '/proc/' + str(pid) + '/cmdline'
    fullpath = ''

    try:
        f = open(procpath, 'r')
        fullpath = f.readline().split('\0')
        f.close()
    except:
        pass

    return fullpath

# TODO: figure out more robust way to do this
path = os.path.split(os.path.abspath(__file__))[0]
def get_ui_dir():
    return os.environ.get('DFEET_DATA_PATH', path + '../share/dfeet/ui')

def get_xslt_dir():
    return os.environ.get('DFEET_XSLT_PATH', path + '../xslt')

def print_method(m):
    def decorator(*args):
        print "call:", m, args
        r = m(*args)
        print "return:", r
        return r
    return decorator
