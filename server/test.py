# -*- coding: utf-8 -*-

import threading
import time
from Tkinter import *


def newWindow():
    root = Tk()
    root.mainloop()



def a():
    count = 0
    while count < 10:

        if count == 5:
            print 'count is 5'
            s = threading.Thread(target=newWindow)
            s.setDaemon(True)
            s.start()

        print count
        count += 1
    time.sleep(5)


q = threading.Thread(target=a)
q.setDaemon(True)
q.start()
