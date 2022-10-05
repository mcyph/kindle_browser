import json
import time
import threading
import aiohttp.web
from os import system
from queue import Queue

from legacy_websockets import main as wsmain


HOST = '0.0.0.0'
PORT = 8000

to_client_queue = Queue()
from_client_queue = Queue()


async def get(request):
    raise aiohttp.web.HTTPFound('/static/index.html')


async def websocket_handler(request):
    print('Websocket connection starting')
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    print('Websocket connection ready')
    i_data = None
    try:
        while True:
            #data = await websocket.receive()
            #if data['type'] == 'websocket.disconnect':
            #    break
            i_data = to_client_queue.get()
            await ws.send_str(json.dumps(i_data,
                                         ensure_ascii=False,
                                         separators=(',', ':')))
    except KeyError:
        if i_data is not None:
            to_client_queue.put(i_data)
        return
    except Exception as ex:
        return ex


def monitor_client_queue():
    while True:
        command = from_client_queue.get()
        if command['type'] not in ('command', 'keyevent'):
            x = command['left']
            y = command['top']

        try:
            if command['type'] == 'mouseMove':
                system(f"DISPLAY=:2 xdotool mousemove {x} {y}")
            elif command['type'] == 'mouseDown':
                system(f"DISPLAY=:2 xdotool mousemove {x} {y}")
                system(f"DISPLAY=:2 xdotool click 1")
            # elif command['type'] in ('mouseUp', 'click') and self.mouse_down:
            #    system(f"DISPLAY=:2 xdotool mousemove {x} {y}")
            #    system(f"DISPLAY=:2 xdotool mouseup")
            elif command['type'] == 'command':
                if command['command'] == 'keyevent':
                    if command['keyEventType'] == 'keydown':
                        modifiers = []
                        if command['shiftKey']:
                            modifiers.append('shift')
                        if command['altKey']:
                            modifiers.append('alt')
                        if command['ctrlKey']:
                            modifiers.append('ctrl')

                        modifiers.append(chr(command['keyCode']).upper() if command['shiftKey'] else chr(command['keyCode']).lower())  # charCode??
                        system(f"DISPLAY=:2 xdotool key {'+'.join(modifiers)}")

                elif command['command'] == 'scroll_up':
                    print("scroll up")
                    system(f"DISPLAY=:2 xdotool key Page_Up")
                elif command['command'] == 'scroll_down':
                    print("scroll down")
                    system(f"DISPLAY=:2 xdotool key Page_Down")
                elif command['command'] == 'forward':
                    system(f"DISPLAY=:2 xdotool key alt+Right")
                elif command['command'] == 'back':
                    system(f"DISPLAY=:2 xdotool key alt+Left")
                elif command['command'] == 'refresh':
                    system(f"DISPLAY=:2 xdotool key F5")
                elif command['command'] == 'top':
                    system(f"DISPLAY=:2 xdotool key Home")
                elif command['command'] == 'navigate':
                    # browser.ExecuteJavascript('location.href = %s' % json.dumps(command['url']))
                    # browser.LoadUrl(command['url'])
                    pass

                elif command['command'] == 'initialFrame':
                    from ScreenStateContext import ScreenStateContext
                    from process_image_for_output import process_image_for_output

                    with ScreenStateContext.lock:
                        to_client_queue.put({
                            'imageData': process_image_for_output(ScreenStateContext.background),
                            'left': 0,
                            'top': 0,
                            'width': ScreenStateContext.screen_x,
                            'height': ScreenStateContext.screen_y,
                        })
                        ScreenStateContext.reset_dirty_rect()
                        ScreenStateContext.ready_for_send = False

                elif command['command'] == 'readyForMore':
                    from ScreenStateContext import ScreenStateContext
                    from process_image_for_output import process_image_for_output
                    print('ready for more sent:', ScreenStateContext.dirty_rect)

                    if ScreenStateContext.dirty_rect:
                        with ScreenStateContext.lock:
                            to_client_queue.put({
                                'imageData': process_image_for_output(ScreenStateContext.background.crop(ScreenStateContext.dirty_rect)),
                                'left': ScreenStateContext.dirty_rect[0],
                                'top': ScreenStateContext.dirty_rect[1],
                                'width': ScreenStateContext.dirty_rect[2] - ScreenStateContext.dirty_rect[0],
                                'height': ScreenStateContext.dirty_rect[3] - ScreenStateContext.dirty_rect[1],
                            })
                            ScreenStateContext.reset_dirty_rect()
                            ScreenStateContext.ready_for_send = False
                    else:
                        with ScreenStateContext.lock:
                            ScreenStateContext.ready_for_send = True
                else:
                    raise Exception(command)
            # else:
            #    raise Exception(command)
        except:
            import traceback
            traceback.print_exc()


thread = threading.Thread(target=wsmain, args=(to_client_queue, from_client_queue))
thread.start()


def main():
    from PIL import Image
    import subprocess
    import legacy_websockets
    from ScreenStateContext import ScreenStateContext
    import xdamage_test

    proc = subprocess.Popen(['Xephyr', '-screen', f'{ScreenStateContext.screen_x}x{ScreenStateContext.screen_y}', ':2'], shell=False)
    pid = proc.pid

    thread = threading.Thread(target=monitor_client_queue, args=())
    thread.start()

    time.sleep(4)

    background = Image.new("L", (ScreenStateContext.screen_x, ScreenStateContext.screen_y), (255,))
    legacy_websockets.background = background

    thread_2 = threading.Thread(target=xdamage_test.main, args=(to_client_queue, pid))
    #xdamage_test.main(to_client_queue, pid)
    thread_2.start()

    #system("DISPLAY=:2 onboard &")
    system(f"DISPLAY=:2 matchbox-window-manager &")
    system(f"DISPLAY=:2 firefox -P Xephyr -width {ScreenStateContext.screen_x} -height {ScreenStateContext.screen_y} &")

    #loop = asyncio.get_event_loop()
    app = aiohttp.web.Application()
    app.add_routes([aiohttp.web.static('/static', './static', show_index=True)])
    app.router.add_route('GET', '/', get)
    app.router.add_route('GET', '/ws', websocket_handler)
    aiohttp.web.run_app(app, host=HOST, port=PORT)


if __name__ == '__main__': 
    main()
