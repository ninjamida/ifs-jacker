CONSOLE_THREADED = True

import time, sys, uselect
if CONSOLE_THREADED:
    import _thread

class IJ_Console:
    def __init__(self):
        self.input_buffer = ""
        self.need_refresh_prompt = True

        self.incoming = []
        self.outgoing = []

        self.poller = uselect.poll()
        self.poller.register(sys.stdin, uselect.POLLIN)

        self.input_prefix = "  Command:"
        self.timestamp_digits = len(self.input_prefix)

        if CONSOLE_THREADED:
            self.thread_lock = _thread.allocate_lock()

    def start_thread(self):
        _thread.start_new_thread(self.execute_thread, ())

    def execute_thread(self):
        self.terminate = False
        self.running = True
        while not self.terminate:
            self.execute()
        self.running = False

    def lock(self):
        if CONSOLE_THREADED:
            self.thread_lock.acquire()

    def release(self):
        if CONSOLE_THREADED:
            self.thread_lock.release()
    
    def execute(self):
        try:
            if len(self.incoming) > 0:
                sys.stdout.write('\r\x1b[K')
                self.lock()
                try:
                    while len(self.incoming) > 0:
                        line = self.incoming.pop(0)
                        line_text = f"{time.ticks_ms():0{self.timestamp_digits}d}  {line}"
                        print(line_text)
                    self.need_refresh_prompt = True
                finally:
                    self.release()

            console_input = self.check_input()
            if console_input != None:
                self.lock()
                try:
                    self.outgoing += [console_input]
                finally:
                    self.release()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"\r{time.ticks_ms():0{self.timestamp_digits}d}  Exception occurred in console: {e}")
    
    def check_input(self) -> str | None:
        if self.need_refresh_prompt:
            sys.stdout.write('\r' + self.input_prefix + '  ' + self.input_buffer)
            self.need_refresh_prompt = False

        while self.poller.poll(0):
            char = sys.stdin.read(1)

            if char in ['\r', '\n']:
                result = self.input_buffer
                self.input_buffer = ""
                self.need_refresh_prompt = True
                print()
                return result
            elif char in ['\x08', '\x7F']:
                if len(self.input_buffer) > 0:
                    self.input_buffer = self.input_buffer[:-1]
                    sys.stdout.write('\b \b')
            elif ord(char) >= 32 and ord(char) < 127:
                self.input_buffer += char
                sys.stdout.write(char)
        
        return None