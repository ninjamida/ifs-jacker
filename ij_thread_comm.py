import _thread

class IJ_Thread_Comm:    
    def __init__(self, channels:int=2):
        self.channel_data = []
        self.channel_lock = []
        for i in range(channels):
            self.channel_data.append([])
            self.channel_lock.append(_thread.allocate_lock())
            
    def get(self, channel:int) -> str | None:
        self.channel_lock[channel].acquire()
        try:
            data = self.channel_data[channel]
            if len(data) == 0:
                return None
            else:
                return data.pop(0)
        finally:
            self.channel_lock[channel].release()
            
    def send(self, channel:int, message:str):
        self.channel_lock[channel].acquire()
        try:
            self.channel_data[channel].append(message)
        finally:
            self.channel_lock[channel].release()
            
    def any(self, channel) -> bool:
        return len(self.channel_data[channel]) > 0
