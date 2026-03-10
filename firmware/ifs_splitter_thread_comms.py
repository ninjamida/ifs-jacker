import ifs_splitter_system_consts as CONSTS
import _thread

class IFSSplitterThreadComms:    
    def __init__(self, config):
        self.config = config
        self.channel_data = []
        self.channel_lock = []
        for i in range(CONSTS.THREADCOMM_CHANNELS):
            self.channel_data.append([])
            self.channel_lock.append(_thread.allocate_lock())
            
    def get(self, channel):
        self.channel_lock[channel].acquire()
        try:
            data = self.channel_data[channel]
            if len(data) == 0:
                return None
            else:
                return data.pop(0)
        finally:
            self.channel_lock[channel].release()
            
    def send(self, channel, message):
        self.channel_lock[channel].acquire()
        try:
            self.channel_data[channel].append(message)
        finally:
            self.channel_lock[channel].release()
            
    def any(self, channel):
        return len(self.channel_data[channel]) > 0
