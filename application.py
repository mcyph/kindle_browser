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
                    modifiers = []
                    if command['shiftKey']:
                        modifiers.append('shift')
                    if command['altKey']:
                        modifiers.append('shift')
                    if command['ctrlKey']:
                        modifiers.append('shift')

                    modifiers.append(chr(command['keyCode']))  # charCode??
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
                else:
                    raise Exception(command)
            # else:
            #    raise Exception(command)
        except:
            import traceback
            traceback.print_exc()


VIEWPORT_HEIGHT = 800
VIEWPORT_WIDTH = 750

thread = threading.Thread(target=wsmain, args=(to_client_queue, from_client_queue))
thread.start()


def main():
    from PIL import Image
    import subprocess
    import legacy_websockets

    proc = subprocess.Popen(['Xephyr', '-screen', f'{VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT}', ':2'], shell=False)
    pid = proc.pid

    thread = threading.Thread(target=monitor_client_queue, args=())
    thread.start()

    time.sleep(4)

    background = Image.new("L", (VIEWPORT_WIDTH, VIEWPORT_HEIGHT), (255,))
    legacy_websockets.background = background

    import xdamage_test
    thread_2 = threading.Thread(target=xdamage_test.main, args=(to_client_queue, pid))
    #xdamage_test.main(to_client_queue, pid)
    thread_2.start()

    #system("DISPLAY=:2 onboard &")
    system(f"DISPLAY=:2 matchbox-window-manager &")
    system(f"DISPLAY=:2 firefox -P Xephyr -width {VIEWPORT_WIDTH} -height {VIEWPORT_HEIGHT} &")

    #loop = asyncio.get_event_loop()
    app = aiohttp.web.Application()
    app.add_routes([aiohttp.web.static('/static', './static', show_index=True)])
    app.router.add_route('GET', '/', get)
    app.router.add_route('GET', '/ws', websocket_handler)
    aiohttp.web.run_app(app, host=HOST, port=PORT)


if __name__ == '__main__': 
    main()
