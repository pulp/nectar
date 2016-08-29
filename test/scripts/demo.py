from __future__ import print_function
from future import standard_library
# run 'python -i demo.py' and see the result. You should see 'start' printed
# and then 'finish'. Then uncomment the monkey patch line and try again. You
# will see the 'start', but never the 'finish'.

import threading
import time

import eventlet
eventlet.monkey_patch()

standard_library.install_aliases()


def foo():
    print('start')
    time.sleep(1)
    print('finish')


thread = threading.Thread(target=foo)
thread.start()
thread.join()
