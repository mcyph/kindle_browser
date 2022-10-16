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

import os
import sys

# Change path so we find Xlib
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import time
import base64
import threading
import traceback
import subprocess
try:
    import thread
except ModuleNotFoundError:
    import _thread as thread
from PIL import Image
from PIL import ImageChops
from Xlib.ext import damage
from Xlib import display, X, Xutil

from src.Timer import Timer
from src.ScreenStateContext import ScreenStateContext
from src.process_image_for_output import process_image_for_output
from src.x_motion_events import run_motion_change_event_listener


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


def send_if_changed(win, to_client_queue):
    with Timer('send_if_changed get_image_from_win'):
        x1, y1, x2, y2 = ScreenStateContext.dirty_rect
        image = get_image_from_win(win, x2-x1, y2-y1, x1, y1)
        if not image:
            ScreenStateContext.reset_dirty_rect()
            return

    if False:
        # TODO: Benchmark this code!
        if image.size == ScreenStateContext.background.size:
            diff = ImageChops.difference(image.convert('L', dither=Image.NONE),
                                         ScreenStateContext.background.convert('L', dither=Image.NONE))
        else:
            diff = ImageChops.difference(image.convert('L', dither=Image.NONE),
                                         ScreenStateContext.background.crop(
                                             (x1, y1, x2, y2)).convert('L', dither=Image.NONE))

        if not diff.getbbox():
            print("IGNORING BECAUSE NOT DIFFERENT ENOUGH: CONDITION 1")
            ScreenStateContext.reset_dirty_rect()
            return

    # elif len(list(i for i in diff.getdata() if i)) < 10:
    #    print("IGNORING BECAUSE NOT DIFFERENT ENOUGH: CONDITION 2", set(diff.getdata()))
    #    continue

    with Timer('send_if_changed paste'):
        ScreenStateContext.paste(image, x1, y1)

    with Timer('send_if_changed crop'):
        img = ScreenStateContext.background.crop(ScreenStateContext.dirty_rect)

    with Timer('send_if_changed process_image_for_output'):
        img_data = process_image_for_output(img)

    with Timer('send_if_changed b64encode'):
        img_data = base64.b64encode(bytes(img_data)).decode('ascii')

    with Timer('send_if_changed put'):
        to_client_queue.put({
            'type': 'image',
            #'imageData': base64.b64encode(gzip.compress(json.dumps(process_image_for_output(
            #    ScreenStateContext.background.crop(ScreenStateContext.dirty_rect))).encode('ascii'))).decode('ascii'),
            'imageData': img_data,
            'left': ScreenStateContext.dirty_rect[0],
            'top': ScreenStateContext.dirty_rect[1],
            'width': img.size[0],
            'height': img.size[1],
        })

    ScreenStateContext.reset_dirty_rect()
    ScreenStateContext.ready_for_send = False


def _image_changed_thread(win, to_client_queue):
    while True:
        #x, y, width, height = q_image_changed.get()
        #ScreenStateContext.add_to_dirty_rect(x, y, x+width, y+height)

        try:
            with ScreenStateContext.lock:
                if ScreenStateContext.ready_for_send and ScreenStateContext.dirty_rect:
                    #print("SENDING:", ScreenStateContext.ready_for_send, ScreenStateContext.dirty_rect)
                    send_if_changed(win, to_client_queue)
        except:
            import traceback
            traceback.print_exc()

        time.sleep(0.3)


#def _send_full_repaints_thread(to_client_queue, window1):
#    from ScreenStateContext import ScreenStateContext
#    while True:
#        img = get_image_from_win(window1, ScreenStateContext.screen_x, ScreenStateContext.screen_y, 0, 0)
#        #print(img)
#        if img:
#            q_image_changed.put((0, 0, ScreenStateContext.screen_x, ScreenStateContext.screen_y))
#        time.sleep(1)


def main(to_client_queue, pid):
    d = display.Display()
    check_ext(d)

    window1_x_id = int(subprocess.check_output(['xdotool', 'search', '--any',
                                                '--pid', str(pid),
                                                '--name', #'Xnest',
                                                'Xephyr on :2.0'
                                                ]).decode('ascii').strip().split('\n')[-1])

    window1 = d.create_resource_object('window', window1_x_id)

    window1.damage_create(damage.DamageReportRawRectangles)
    window1.set_wm_normal_hints(
        flags=(Xutil.PPosition | Xutil.PSize | Xutil.PMinSize),
        min_width=50,
        min_height=50
    )

    t = threading.Thread(target=_image_changed_thread, args=[window1, to_client_queue])
    t.start()

    t = threading.Thread(target=run_motion_change_event_listener, args=[to_client_queue])  # window1
    t.start()

    #t = threading.Thread(target=_send_full_repaints_thread, args=(to_client_queue, window1))
    #t.start()

    while 1:
        try:
            with Timer('xdamage event'):
                event = d.next_event()
                #print("EVENT:", event)
                if event.type == X.Expose:
                    if event.count == 0:
                        pass
                elif event.type == d.extension_event.DamageNotify:
                    ScreenStateContext.add_to_dirty_rect(event.area.x,
                                                         event.area.y,
                                                         event.area.width + event.area.x,
                                                         event.area.height + event.area.y)
                elif event.type == X.DestroyNotify:
                    sys.exit(0)
                else:
                    print(f"WARNING: Unknown event type: {event.type}")
            time.sleep(0.2)
        except:
            import traceback
            traceback.print_exc()
            time.sleep(0.3)

