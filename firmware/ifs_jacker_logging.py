import time
import ifs_jacker_system_consts as CONSTS

class IFSJackerLogging:
    def __init__(self, config):
        self.config = config
        self.last_entry_time = time.ticks_ms()
        self.log_queue = []

    def log(self, line):
        if self.config.logging:
            self.last_entry_time = time.ticks_ms()
            self.log_queue.append(line)
            if len(self.log_queue) >= CONSTS.LOG_FLUSH_COUNT:
                self.flush_logs()

    def check_log_flush_time(self):
        if len(self.log_queue) > 0:
            if time.ticks_diff(time.ticks_ms(), self.last_entry_time) >= CONSTS.LOG_FLUSH_TIME * 1000:
                self.flush_logs()

    def flush_logs(self):
        if self.config.logging:
            self.log_queue = []