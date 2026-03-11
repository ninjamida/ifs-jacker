import time, sys, uselect
import ifs_splitter_system_consts as CONSTS

class IFSSplitterConsole:
    def __init__(self, config, threadcomm, threadcomm_id, main_threadcomm_id, logging):
        self.config = config
        self.terminate = False
        self.input_buffer = ""
        self.need_refresh_prompt = True

        self.poller = uselect.poll()
        self.poller.register(sys.stdin, uselect.POLLIN)

        self.threadcomm = threadcomm
        self.logging = logging
        self.threadcomm_id = threadcomm_id
        self.main_threadcomm_id = main_threadcomm_id

        self.is_running = False
    
    def execute(self):
        self.is_running = True
        while not self.terminate:
            try:
                if self.threadcomm.any(self.threadcomm_id):
                    sys.stdout.write('\r\x1b[K')
                    while self.threadcomm.any(self.threadcomm_id):
                        line = self.threadcomm.get(self.threadcomm_id)
                        line_text = f"{time.ticks_ms():0{CONSTS.TIMESTAMP_DIGITS}d}  {line}"
                        if line != "Z99":
                            print(line_text)
                            self.logging.log(line_text)
                        if line == "Z99" or line.startswith('^^<< Z99 ok.'):
                            self.terminate = True
                            print()
                    self.need_refresh_prompt = True

                if not self.terminate:
                    console_input = self.check_input()
                if console_input != None:
                    self.threadcomm.send(self.main_threadcomm_id, console_input)
                    self.logging.log(f"{CONSTS.CONSOLE_INPUT_PREFIX}  {console_input}")
                    if console_input.startswith("Z99") and "F1" in console_input:
                        self.terminate = True
            except KeyboardInterrupt:
                raise
            except Exception as e:
                try:
                    print(f"\r{CONSTS.CONSOLE_INPUT_PREFIX}  Exception {e}")
                except:
                    pass
            self.logging.check_log_flush_time()
        self.is_running = False
    
    def check_input(self):
        if self.need_refresh_prompt:
            sys.stdout.write('\r' + CONSTS.CONSOLE_INPUT_PREFIX + '  ' + self.input_buffer)
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