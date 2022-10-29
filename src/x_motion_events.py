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
from src.pyxcursor.pyxcursor import Xcursor


local_dpy = display.Display()
record_dpy = display.Display()
root = local_dpy.screen().root
q = Queue()


def get_absolute_geometry(win):
    """
    Returns the (x, y, height, width) of a window relative to the top-left
    of the screen.

    https://stackoverflow.com/questions/12775136/get-window-position-and-size-in-python-with-xlib
    """
    geom = win.get_geometry()
    (x, y) = (geom.x, geom.y)
    while True:
        parent = win.query_tree().parent
        pgeom = parent.get_geometry()
        x += pgeom.x
        y += pgeom.y
        if parent.id == root.id:
            break
        win = parent
    return x, y


def _check_queue(x_display, window1_x_id, to_client_cursor_queue):
    d = display.Display()
    window = d.create_resource_object('window', window1_x_id)
    x_cursor = Xcursor(display=x_display.encode('ascii'))
    old_cursor_data = None

    while True:
        try:
            event = q.get()
            while not q.empty():
                event = q.get()

            #with ScreenStateContext.lock:
            #print("MotionNotify send", event.root_x, event.root_y)

            if event is not None:
                geometry_x, geometry_y = get_absolute_geometry(window)
                #print(geometry_x, geometry_y)
                to_client_cursor_queue.put({
                    'type': 'cursor_move',
                    'absolute_x': event.root_x-geometry_x,
                    'absolute_y': event.root_y-geometry_y,
                    'relative_x': event.root_x-geometry_x,
                    'relative_y': event.root_y-geometry_y,
                })

            cursor_data = x_cursor.getImageAsBase64()
            if cursor_data != old_cursor_data:
                old_cursor_data = cursor_data
                to_client_cursor_queue.put({
                    'type': 'cursor_change',
                    'data': cursor_data,
                })
        except:
            import traceback
            traceback.print_exc()

        time.sleep(0.05)


def _cursor_poller():
    # Make sure cursor image is updated periodically
    # TODO: Use events from xlib (if possible)
    while True:
        time.sleep(0.5)
        q.put(None)


def run_motion_change_event_listener(x_display, window1_x_id, to_client_cursor_queue):
    t = threading.Thread(target=_check_queue,
                         args=[x_display, window1_x_id, to_client_cursor_queue])
    t.start()

    t = threading.Thread(target=_cursor_poller,
                         args=[])
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

