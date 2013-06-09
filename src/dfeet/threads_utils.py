from gi.repository import Gdk
from functools import wraps
from threading import Thread


class ThreadLock(object):
    def __enter__(self, *args, **kwds):
        Gdk.threads_init()
        Gdk.threads_enter()
    
    def __exit__(self, *args, **kwds):
        Gdk.threads_leave()


def thread_locking(fn):
    @wraps(fn)
    def thread_locking_fn(*args, **kwds):
        with ThreadLock():
            return fn(*args, **kwds)
    return thread_locking_fn


class Callback(Thread):
    '''
    Runs callback in new threads
    '''
    def __init__(self, *callbacks):
        super(Callback, self).__init__()
        self.callbacks = list(callbacks)
        self.args = []
        self.kwds = {}

    def __call__(self, *args, **kwds):
        self.args = args
        self.kwds = kwds
        self.start()
        
    def run(self):
        for callback in self.callbacks:
            callback(*self.args, **self.kwds)


def as_new_thread(fn):
    @wraps(fn)
    def in_new_thread(*args, **kwds):
        cb = Callback(fn)
        cb(*args, **kwds)
    return in_new_thread
