import io
import json
import base64
import threading
import aiohttp.web
from PIL import Image
from queue import Queue
from cefpython3 import cefpython

import legacy_websockets
from legacy_websockets import main as wsmain
from process_image_for_output import process_image_for_output


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
    try:
        while True:
            #data = await websocket.receive()
            #if data['type'] == 'websocket.disconnect':
            #    break
            i_data = to_client_queue.get()
            await ws.send_str(json.dumps(i_data))
    except Exception as ex:
        return ex


class ClientHandler:
    """A client handler is required for the browser to do built in callbacks back into the application."""
    browser = None
    image = None
    width = None
    height = None
    screenshot_fpath = None

    def __init__(self, browser, width, height, screenshot_fpath):
        self.browser = browser
        self.width = width
        self.height = height
        self.screenshot_fpath = screenshot_fpath
        
        def monitor_client_queue():
            while True:
                command = from_client_queue.get()
                if command['type'] not in ('command', 'keyevent'):
                    x = command['left']
                    y = command['top']
                
                try:
                    if command['type'] == 'mouseMove':
                        browser.SendMouseMoveEvent(x, y, False, cefpython.EVENTFLAG_NONE)
                        self.mouse_down = True
                    elif command['type'] == 'mouseDown':
                        browser.SendMouseMoveEvent(x, y, False, cefpython.EVENTFLAG_NONE)
                        self.mouse_down = True
                    elif command['type'] in ('mouseUp', 'click') and self.mouse_down:
                        browser.SendMouseMoveEvent(x, y, False, cefpython.EVENTFLAG_LEFT_MOUSE_BUTTON)
                        browser.SendMouseClickEvent(x, y, cefpython.MOUSEBUTTON_LEFT, False, 1, cefpython.EVENTFLAG_LEFT_MOUSE_BUTTON)
                        browser.SendMouseClickEvent(x, y, cefpython.MOUSEBUTTON_LEFT, True, 1, cefpython.EVENTFLAG_LEFT_MOUSE_BUTTON)
                        self.mouse_down = False
                    elif command['type'] == 'command':
                        if command['command'] == 'keyevent':
                            modifiers = 0
                            if command['shiftKey']:
                                modifiers |= cefpython.EVENTFLAG_SHIFT_DOWN
                            if command['altKey']:
                                modifiers |= cefpython.EVENTFLAG_ALT_DOWN
                            if command['ctrlKey']:
                                modifiers |= cefpython.EVENTFLAG_CTRL_DOWN
                            
                            browser.SendKeyEvent({
                                'type': {
                                    'keydown': cefpython.KEYEVENT_KEYDOWN,
                                    'keyup': cefpython.KEYEVENT_KEYUP,
                                    'keypress': cefpython.KEYEVENT_CHAR,
                                }[command['keyEventType']],
                                'modifiers': modifiers,
                                'windows_key_code': command['keyCode'],
                                'native_key_code': command['keyCode'],
                                'character': command['charCode'],
                                'focus_on_editable_field': False
                            })
                        elif command['command'] == 'scroll_up':
                            print("scroll up")
                            browser.ExecuteJavascript('document.documentElement.scrollTop -= 550')
                        elif command['command'] == 'scroll_down':
                            print("scroll down")
                            browser.ExecuteJavascript('document.documentElement.scrollTop += 550')
                        elif command['command'] == 'forward':
                            browser.GoForward()
                        elif command['command'] == 'back':
                            browser.GoBack()
                        elif command['command'] == 'refresh':
                            browser.Reload()
                        elif command['command'] == 'top':
                            browser.ExecuteJavascript('document.documentElement.scrollTop = 0')
                        elif command['command'] == 'navigate':
                            browser.ExecuteJavascript('location.href = %s' % json.dumps(command['url']))
                            #browser.LoadUrl(command['url'])
                        else:
                            raise Exception(command)
                    #else:
                    #    raise Exception(command)
                except:
                    import traceback
                    traceback.print_exc()

        thread = threading.Thread(target=monitor_client_queue, args=())
        thread.start()
    
    def OnLoadingStateChange(self, browser, is_loading, **_):
        if is_loading:
            print("Page loading complete - start visiting cookies")
            manager = cefpython.CookieManager.GetGlobalManager()
            # Must keep a strong reference to the CookieVisitor object
            # while cookies are being visited.
            self.cookie_visitor = CookieVisitor()
            # Visit all cookies
            result = manager.VisitAllCookies(self.cookie_visitor)
            if not result:
                print("Error: could not access cookies")
        
    def OnLoadingProgressChange(self, browser, progress):
        if round(browser.GetZoomLevel()) != 4:
            browser.SetZoomLevel(4.0)

    def OnPaint(self, browser, element_type, dirty_rects, paint_buffer, width, height):
        if element_type == cefpython.PET_POPUP:
            print("width=%s, height=%s" % (width, height))
        elif element_type == cefpython.PET_VIEW:
            self.image = paint_buffer.GetString(mode="rgba", origin="top-left")
            image = Image.frombytes("RGBA", (width, height), self.image, "raw", "RGBA", 0, 1)
            background = Image.new("L", image.size, (255,))
            background.paste(image, mask=image.split()[3]) # 3 is the alpha channel
            legacy_websockets.background = background
            
            for dirty_rect in dirty_rects:
                # list[[x,y,width,height],[..]]
                cropped_background = background.crop((dirty_rect[0], dirty_rect[1], 
                                                      dirty_rect[0]+dirty_rect[2], dirty_rect[1]+dirty_rect[3]))
                to_client_queue.put({
                    'imageData': process_image_for_output(cropped_background),
                    'left': dirty_rect[0], 
                    'top': dirty_rect[1],
                    'width': dirty_rect[2], 
                    'height': dirty_rect[3],
                })
        else:
            raise Exception("Unknown paintElementType: %s" % element_type)

    def GetViewRect(self, browser, rect_out):
        width = self.width
        height = self.height
        rect_out.append(0)
        rect_out.append(0)
        rect_out.append(width)
        rect_out.append(height)
        return True

    def GetScreenPoint(self, browser, view_x, view_y, screen_coordinates_out):
        print("GetScreenPoint()")
        return False

    def OnLoadEnd(self, browser, frame, http_code):
        #image.save(self.screenshot_fpath, "PNG")
        #cefpython.QuitMessageLoop()
        pass

    def OnLoadError(self, browser, frame, error_code, error_text_out, failed_url):
        print("load error", browser, frame, error_code, error_text_out, failed_url)


def run_browser():
    cefpython.g_debug = False
    cefpython.Initialize(
        {
            "log_severity": cefpython.LOGSEVERITY_INFO, # LOGSEVERITY_VERBOSE
            #"log_file": GetApplicationPath("debug.log"), # Set to "" to disable.
            "release_dcheck_enabled": False, # Enable only when debugging.
            # This directories must be set on Linux
            "locales_dir_path": cefpython.GetModuleDirectory()+"/locales",
            "resources_dir_path": cefpython.GetModuleDirectory(),
            "multi_threaded_message_loop": False,
            "browser_subprocess_path": "%s/%s" % (cefpython.GetModuleDirectory(), "subprocess"),
            #"auto_zooming": "2.0",
            "cache_path": "./browser_cache",
        }, 
        switches={
            # https://pastebin.com/JUrqiMqW
            
            #'disable-features': 'TouchpadAndWheelScrollLatching,AsyncWheelEvents', 
            'enable-media-stream': '',
            "disable-threaded-scrolling":'',
            'disable-touch-adjustment':'',#TouchpadAndWheelScrollLatching':'',
            "disable-smooth-scrolling":"",
            "disable-AsyncWheelEvents":'',
            # GPU acceleration is not supported in OSR mode, so must disable
            # it using these Chromium switches (Issue #240 and #463)
            "disable-gpu": "",
            "disable-gpu-compositing": "",
            # Tweaking OSR performance by setting the same Chromium flags
            # as in upstream cefclient (Issue #240).
            "enable-begin-frame-scheduling": "",
            #"disable-surfaces": "",  # This is required for PDF ext to work
            "disable-web-security":""
        })

    width = 1236
    height = 1648 - 220
    windowInfo = cefpython.WindowInfo()
    windowInfo.SetAsOffscreen(0)

    browserSettings = {
        'windowless_frame_rate': 3,
        "web_security_disabled": True,
        "file_access_from_file_urls_allowed": "",
        "universal_access_from_file_urls_allowed": "",
    }
    browser = cefpython.CreateBrowserSync(windowInfo, browserSettings, navigateUrl="https://news.abc.net.au")
    browser.SendFocusEvent(True)
    
    browser.SetClientHandler(ClientHandler(browser, width, height, "screenshot.png"))
    browser.WasResized()
    cefpython.MessageLoop()
    cefpython.Shutdown()


thread = threading.Thread(target=run_browser, args=())
thread.start()
thread = threading.Thread(target=wsmain, args=(to_client_queue, from_client_queue))
thread.start()


def main():
    #loop = asyncio.get_event_loop()
    app = aiohttp.web.Application()
    app.add_routes([aiohttp.web.static('/static', './static', show_index=True)])
    app.router.add_route('GET', '/', get)
    app.router.add_route('GET', '/ws', websocket_handler)
    aiohttp.web.run_app(app, host=HOST, port=PORT)


class CookieVisitor(object):
    def Visit(self, cookie, count, total, delete_cookie_out):
        """This callback is called on the IO thread."""
        print("Cookie {count}/{total}: '{name}', '{value}'"
              .format(count=count+1, total=total, name=cookie.GetName(),
                      value=cookie.GetValue()))
        # Set a cookie named "delete_me" and it will be deleted.
        # You have to refresh page to see whether it succeeded.
        if cookie.GetName() == "delete_me":
            # 'delete_cookie_out' arg is a list passed by reference.
            # Set its '0' index to True to delete the cookie.
            delete_cookie_out[0] = True
            print("Deleted cookie: {name}".format(name=cookie.GetName()))
        # Return True to continue visiting more cookies
        return True


if __name__ == '__main__': 
    main()
    