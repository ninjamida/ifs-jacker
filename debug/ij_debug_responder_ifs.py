class IJDR_IFS:
    def respond(self, message: str, receive_queue: list[str]):
        response = None
        channel = '?'

        params = message.split()
        for param in params:
            if param.startswith('C'):
                channel = param[1:]
                break

        if message.startswith('F10'):
            response = f'F10 ok. FFS channel {channel} feeding.'
        if message.startswith('F11'):
            response = f'F11 ok. FFS channel {channel} exiting.'
        if message.startswith('F13'):
            response = 'F13 ok. FFS_state: 5 silk_state: 11 chan: 2 ffs_channels_insert: 0 stall_state: 0 jinsi_GCONF: 000001dc qiehuan_GCONF: 000001dc'
        if message.startswith('F15'):
            response = 'F15 ok.'
        if message.startswith('F18'):
            response = 'F18 ok'
        if message.startswith('F23'):
            response = f'F23 ok. chan {channel}.'
        if message.startswith('F24'):
            response = f'F24 ok. chan {channel}.'
        if message.startswith('F39'):
            response = f'F39 ok. FFS channel {channel} release.'
        if message.startswith('F112'):
            response = 'F112 ok'
        
        if response:
            receive_queue.append(response)

class IJDR_IFS2(IJDR_IFS):
    def respond(self, message: str, receive_queue: list[str]):
        if message.startswith('F13'):
            receive_queue.append('F13 ok. FFS_state: 5 silk_state: 6 chan: 3 ffs_channels_insert: 0 stall_state: 0 jinsi_GCONF: 000001dc qiehuan_GCONF: 000001dc')
        else:
            return super().respond(message, receive_queue)