import time, sys, uselect
from util import get_traceback_string

class IJ_Console:
    def __init__(self) -> None:
        self.queue = []

        self.poller = uselect.poll()
        self.poller.register(sys.stdin, uselect.POLLIN)

        self.exclude_categories: list[str] = []
        self.include_categories: list[str] = []
        self.input_buffer = ''

    def check_category(self, category: str) -> bool:
        if category == '':
            return True
        if category in self.include_categories:
            return True
        if len(self.include_categories) == 0 and category not in self.exclude_categories:
            return True
        return False

    def print(self, message: str, category: str):
        if self.check_category(category):
            self.queue.append(f'{time.ticks_ms():0{10}d}   {message}')

    def print_exception(self, e: Exception, origin: str | None = None):
        if origin:
            self.print(f'{e.__class__.__name__} occurred in {origin}', 'error')
        else:
            self.print(f'{e.__class__.__name__} occurred', 'error')
        for line in get_traceback_string(e):
            self.print(line, 'error')

    def flush(self):
        if len(self.queue) > 0:
            print('\n'.join(self.queue))
            self.queue.clear()

    def get_input(self) -> str | None:
        while self.poller.poll(0):
            char = sys.stdin.read(1)

            if char in ['\r', '\n']:
                result = self.input_buffer
                self.input_buffer = ""
                return result
            elif char in ['\x08', '\x7F']:
                if len(self.input_buffer) > 0:
                    self.input_buffer = self.input_buffer[:-1]
            elif ord(char) >= 32 and ord(char) < 127:
                self.input_buffer += char

        return None

_console = None

def get_console() -> IJ_Console:
    global _console
    if _console is None:
        _console = IJ_Console()
    return _console