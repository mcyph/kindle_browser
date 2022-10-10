#!/usr/bin/python
#
# examples/xdamage.py -- demonstrate damage extension
#
#    Copyright (C) 2019 Mohit Garg <mrmohitgarg1990@gmail.com>
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


# Python 2/3 compatibility.
from __future__ import print_function

import sys
import os
import subprocess
import threading
from queue import Queue

# Change path so we find Xlib
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from Xlib import display, X, Xutil

try:
    import thread
except ModuleNotFoundError:
    import _thread as thread

from Xlib.ext import damage
from PIL import Image
import traceback


def get_image_from_win(win, pt_w, pt_h, pt_x=0, pt_y=0):
    #print(pt_w, pt_h, pt_x, pt_y)
    try:
        raw = win.get_image(pt_x, pt_y, pt_w, pt_h, X.ZPixmap, 0xffffffff)
        image = Image.frombytes("RGB", (pt_w, pt_h), raw.data, "raw", "BGRX")
        return image
    except Exception:
        traceback.print_exc()


def check_ext(disp):
    # Check for extension
    if not disp.has_extension('DAMAGE'):
        sys.stderr.write('server does not have the DAMAGE extension\n')
        sys.stderr.write("\n".join(disp.list_extensions()))

        if disp.query_extension('DAMAGE') is None:
            sys.exit(1)
    else:
        r = disp.damage_query_version()
        print('DAMAGE version {}.{}'.format(r.major_version, r.minor_version))


q_image_changed = Queue()


def _image_changed_thread(to_client_queue):
    from PIL import ImageChops
    from ScreenStateContext import ScreenStateContext
    from process_image_for_output import process_image_for_output

    while True:
        x, y, image = q_image_changed.get()

        if image.size == ScreenStateContext.background.size:
            diff = ImageChops.difference(image.convert('L', dither=Image.NONE),
                                         ScreenStateContext.background.convert('L', dither=Image.NONE))
        else:
            diff = ImageChops.difference(image.convert('L', dither=Image.NONE),
                                         ScreenStateContext.background.crop((x, y, x+image.size[0], y+image.size[1])).convert('L', dither=Image.NONE))

        if not diff.getbbox():
            print("IGNORING BECAUSE NOT DIFFERENT ENOUGH: CONDITION 1")
            continue
        elif len(set(diff.getdata())) < 10:
            print("IGNORING BECAUSE NOT DIFFERENT ENOUGH: CONDITION 2", set(diff.getdata()))
            continue

        with ScreenStateContext.lock:
            ScreenStateContext.paste(image, x, y)

            if ScreenStateContext.ready_for_send:
                ScreenStateContext.ready_for_send = False
                to_client_queue.put({
                    'imageData': process_image_for_output(
                        ScreenStateContext.background.crop(ScreenStateContext.dirty_rect)),
                    'left': ScreenStateContext.dirty_rect[0],
                    'top': ScreenStateContext.dirty_rect[1],
                    'width': ScreenStateContext.dirty_rect[2] - ScreenStateContext.dirty_rect[0],
                    'height': ScreenStateContext.dirty_rect[3] - ScreenStateContext.dirty_rect[1],
                })
                ScreenStateContext.reset_dirty_rect()


def main(to_client_queue, pid):
    t = threading.Thread(target=_image_changed_thread, args=(to_client_queue,))
    t.start()

    d = display.Display()
    check_ext(d)

    window1_x_id = int(subprocess.check_output(['xdotool', 'search', '--any',
                                                '--pid', str(pid),
                                                '--name', 'Xephyr on :2.0']))

    window1 = d.create_resource_object('window', window1_x_id)

    window1.damage_create(damage.DamageReportRawRectangles)
    window1.set_wm_normal_hints(
        flags=(Xutil.PPosition | Xutil.PSize | Xutil.PMinSize),
        min_width=50,
        min_height=50
    )

    while 1:
        event = d.next_event()
        if event.type == X.Expose:
            if event.count == 0:
                pass
        elif event.type == d.extension_event.DamageNotify:
            get_area = event.area.width, event.area.height, event.area.x, event.area.y
            #get_area = ScreenStateContext.screen_x, ScreenStateContext.screen_y, 0, 0
            print("DAMAGE DETECTED:", get_area)

            image = get_image_from_win(window1, *get_area)
            q_image_changed.put((event.area.x, event.area.y, image))
        elif event.type == X.DestroyNotify:
            sys.exit(0)
        else:
            raise Exception(f"Unknown event type: {event.type}")

