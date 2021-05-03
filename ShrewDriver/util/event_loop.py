from __future__ import division
import sys
sys.path.append("..")

import threading
from collections import deque

from cond_event import CondEvent

class EventLoop(object):
    """
    Has a deque of CondEvents. 
    Feed it CondEvents and it will execute them.    
    """
    
    def __init__(self):
        self.queue = deque()
        self.c = threading.Condition()
        self.done = False #thread termination flag

    def loop(self):
        """
        In most cases you will want to run this inside its own thread.
        """
        while not self.done:
            evt = self.queue.popleft()
            if evt.__class__ == CondEvent:
                evt.attempt()
            elif type(evt) == str:
                print str
            else:
                # It may just be a function for us to call.
                (evt, args) = (None, None) #umm, there was supposed to be something here I think
            if evt == None:
                self.c.wait()
            
    def add(self, evt):
        self.queue.append(evt)
        self.c.notify()

if __name__ == "__main__":
    #test speed
    
    #test threading
    pass

