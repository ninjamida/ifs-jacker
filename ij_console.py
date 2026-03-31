import time, sys, uselect
from ij_thread_comm import IJ_Thread_Comm

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

    def execute_thread(self, threadcomm: IJ_Thread_Comm, threadcomm_in: int, threadcomm_out: int):
        self.terminate = False
        self.running = True
        while not self.terminate:
            while threadcomm.any(threadcomm_in):
                self.incoming.append(threadcomm.get(threadcomm_in))
            self.execute()
            while len(self.outgoing) > 0:
                threadcomm.send(threadcomm_out, self.outgoing.pop(0))
        self.running = False
    
    def execute(self):
        try:
            if len(self.incoming) > 0:
                sys.stdout.write('\r\x1b[K')
                while len(self.incoming) > 0:
                    line = self.incoming.pop(0)
                    line_text = f"{time.ticks_ms():0{self.timestamp_digits}d}  {line}"
                    print(line_text)
                self.need_refresh_prompt = True

            console_input = self.check_input()
            if console_input != None:
                if console_input.startswith("Z4 ") or console_input == "Z4":
                    print()
                    confirm = input("Proceed with config? IFS Jacker will reboot immediately on completion. (Y/N)")
                    if confirm.casefold().startswith('y'):
                        raise NotImplementedError("Z4 not yet implemented in V1.x")
                else:
                    self.outgoing += [console_input]
        except KeyboardInterrupt:
            raise
        except Exception as e:
            try:
                print(f"\r{self.input_prefix}  Exception {e}")
            except:
                pass
    
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