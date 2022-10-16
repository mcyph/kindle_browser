#!/usr/bin/python
#
# examples/record_demo.py -- demonstrate record extension
#
#    Copyright (C) 2006 Alex Badea <vamposdecampos@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; either version 2.1
# of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
#    Free Software Foundation, Inc.,
#    59 Temple Place,
#    Suite 330,
#    Boston, MA 02111-1307 USA

'''
Simple demo for the RECORD extension
Not very much unlike the xmacrorec2 program in the xmacro package.
'''


# Python 2/3 compatibility.
from __future__ import print_function

import os
import sys
import time
import threading
from queue import Queue

# Change path so we find Xlib
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from Xlib import X, XK, display
from Xlib.ext import record
from Xlib.protocol import rq

from src.ScreenStateContext import ScreenStateContext


local_dpy = display.Display()
record_dpy = display.Display()
q = Queue()


def _check_queue(to_client_queue):
    while True:
        try:
            event = q.get()
            while not q.empty():
                event = q.get()
            with ScreenStateContext.lock:
                #print("MotionNotify send", event.root_x, event.root_y)
                to_client_queue.put({
                    'type': 'cursor_move',
                    'absolute_x': event.root_x,
                    'absolute_y': event.root_y,
                    'relative_x': event.root_x,
                    'relative_y': event.root_y,
                })
        except:
            import traceback
            traceback.print_exc()

        time.sleep(0.05)


def run_motion_change_event_listener(to_client_queue):
    t = threading.Thread(target=_check_queue,
                         args=[to_client_queue])
    t.start()

    def record_callback(reply):
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            print("* received swapped protocol data, cowardly ignored")
            return
        if not len(reply.data) or reply.data[0] < 2:
            # not an event
            return

        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value(data, record_dpy.display, None, None)
            if event.type == X.MotionNotify:
                #print("MotionNotify", event.root_x, event.root_y)
                q.put(event)

    # Check if the extension is present
    if not record_dpy.has_extension("RECORD"):
        print("RECORD extension not found")
        sys.exit(1)
    r = record_dpy.record_get_version(0, 0)
    print("RECORD extension version %d.%d" % (r.major_version, r.minor_version))

    # Create a recording context; we only want key and mouse events
    ctx = record_dpy.record_create_context(
        0,
        [record.AllClients],
        [{
            'core_requests': (0, 0),
            'core_replies': (0, 0),
            'ext_requests': (0, 0, 0, 0),
            'ext_replies': (0, 0, 0, 0),
            'delivered_events': (0, 0),
            'device_events': (X.KeyPress,
                              X.MotionNotify,),
            'errors': (0, 0),
            'client_started': False,
            'client_died': False,
        }]
    )

    # Enable the context; this only returns after a call to record_disable_context,
    # while calling the callback function in the meantime
    record_dpy.record_enable_context(ctx, record_callback)

    # Finally free the context
    record_dpy.record_free_context(ctx)

