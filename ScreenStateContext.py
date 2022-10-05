from PIL import Image
import _thread


class _ScreenStateContext:
    def __init__(self, screen_x, screen_y):
        self.screen_x = screen_x
        self.screen_y = screen_y
        self.background = Image.new("L", (screen_x, screen_y), (255,))
        self.reset_dirty_rect()
        self.ready_for_send = False
        self.lock = _thread.allocate_lock()

    def reset_dirty_rect(self):
        self.dirty_rect = None

    def add_to_dirty_rect(self, x1, y1, x2, y2):
        if self.dirty_rect:
            if x1 < self.dirty_rect[0]:
                self.dirty_rect[0] = x1
            if y1 < self.dirty_rect[1]:
                self.dirty_rect[1] = y1
            if x2 > self.dirty_rect[2]:
                self.dirty_rect[2] = x2
            if y2 > self.dirty_rect[3]:
                self.dirty_rect[3] = y2
        else:
            self.dirty_rect = [x1, y1, x2, y2]

    def paste(self, image, x, y):
        self.background.paste(image, (x, y))
        self.add_to_dirty_rect(x, y, x+image.width, y+image.height)


ScreenStateContext = _ScreenStateContext(750, 800)
