from ij_printer_base import IJP_Text_Based
from ij_comm_base import IJCI_Base

class IJP_AD5X(IJP_Text_Based):
    def __init__(self, connection: IJCI_Base):
        super().__init__(connection=connection, seperator=None)

    def _translate_in_channel(self, elements: list[str], command: str) -> dict[str, str]:
        result = {'command': command}
        for param in elements[1:]:
            if param.startswith('C'):
                result['channel'] = param[1:]
        
        return result

    def _translate_in_channel_length_speed(self, elements: list[str], command: str) -> dict[str, str]:
        result = {'command': command}
        channel = None
        length = None
        speed = None
        for param in elements[1:]:
            if param.startswith('C'):
                result['channel'] = str(int(param[1:]) - 1)
            if param.startswith('L'):
                result['channel'] = param[1:]
            if param.startswith('S'):
                result['channel'] = param[1:]
        
        return result
    
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base) -> IJP_AD5X:
        return IJP_AD5X(connection)

    def translate_in_F10(self, elements: list[str]) -> dict[str, str]:
        return self._translate_in_channel_length_speed(elements, 'mmu_insert_filament')
    
    def translate_in_F11(self, elements: list[str]) -> dict[str, str]:
        return self._translate_in_channel_length_speed(elements, 'mmu_withdraw_filament')
    
    def translate_in_F13(self, elements: list[str]) -> dict[str, str]:
        return {'command': 'mmu_get_status'}
    
    def translate_in_F15(self, elements: list[str]) -> dict[str, str]:
        return {'command': 'mmu_reset_drivers'}
    
    def translate_in_F18(self, elements: list[str]) -> dict[str, str]:
        return {'command': 'mmu_release_all_channels'}
    
    def translate_in_F23(self, elements: list[str]) -> dict[str, str]:
        return self._translate_in_channel(elements, 'mmu_mark_active_channel')
    
    def translate_in_F24(self, elements: list[str]) -> dict[str, str]:
        return self._translate_in_channel(elements, 'mmu_clamp_channel')
    
    def translate_in_F39(self, elements: list[str]) -> dict[str, str]:
        return self._translate_in_channel(elements, 'mmu_release_channel')
    
    def translate_in_F112(self, elements: list[str]) -> dict[str, str]:
        return {'command': 'mmu_halt_movement'}
    
    def translate_in_Z0(self, elements: list[str]) -> dict[str, str] | None:
        if len(elements) < 2:
            return None
        result = {'command': elements[1]}
        for param in elements[2:]:
            param_elements = param.split('=', 1)
            if len(param_elements) == 2:
                result[param_elements[0]] = param_elements[1]
            else:
                result[param_elements[0]] = ''
        return result

    def translate_in_Z1(self, elements: list[str]) -> dict[str, str]:
        return {'command': 'ij_get_status'}
    
    def translate_out_mmu_response_insert_filament(self, elements: dict[str, str]) -> str:
        channel_index = elements.get('channel', None)
        if channel_index == None:
            return 'F10 ok.'
        else:
            return f'F10 ok. FFS channel {int(channel_index) + 1} feeding.'
        
    def translate_out_mmu_response_withdraw_filament(self, elements: dict[str, str]) -> str:
        channel_index = elements.get('channel', None)
        if channel_index == None:
            return 'F11 ok.'
        else:
            return f'F11 ok. FFS channel {int(channel_index) + 1} exiting.'
        
    def translate_out_mmu_response_get_status(self, elements: dict[str, str]) -> str:
        # States: (some can be +11*channel to indicate a specific channel)
        # 3 - Querying
        # 5 - Everything OK
        # 7 - (18, 29, etc) Channel clamped
        # 11 - (22, 33, etc) Channel loading
        # 12 - (23, 34, etc) Channel released
        # 15 - (26, 37, etc) Channel unloading
        # 127 - Driver error (does NOT conflict with the +11-able ones)

        global_state = elements.get('global_state', 'ok')
        if global_state == 'querying':
            result_state = 3
        elif global_state == 'driver_error':
            result_state = 127
        else:
            result_state = 5

        result_silk = 0
        result_chan = int(elements.get('active_channel', '0'))
        result_channels_insert = 0
        result_stall_state = 0

        i = 0
        while f'channel_{i}_present' in elements:
            try:
                bitmask = 1 << i
                prefix = f'channel_{i}_'
                if elements.get(prefix + 'present', 'False') == 'True':
                    result_silk |= bitmask
                if elements.get(prefix + 'need_insert', 'False') == 'True':
                    result_channels_insert |= bitmask
                if elements.get(prefix + 'stall', 'False') == 'True':
                    result_stall_state |= bitmask
                if result_state == 5 and i == result_chan:
                    channel_state = elements.get(prefix + 'state', 'ok')
                    if channel_state == 'inserting':
                        result_state = 11 + (11 * i)
                    if channel_state == 'withdrawing':
                        result_state = 15 + (11 * i)
                    if channel_state == 'clamped':
                        result_state = 7 + (11 * i)
                    if channel_state == 'released':
                        result_state = 12 + (11 * i)
            finally:
                i += 1

        return f'F13 ok. FFS_state: {result_state} silk_state: {result_silk} chan: {result_chan} ' + \
            f'ffs_channels_insert: {result_channels_insert} stall_state: {result_stall_state} ' + \
            'jinsi_GCONF: 000001dc qiehuan_GCONF: 000001dc'

    def translate_out_mmu_response_reset_drivers(self, elements: dict[str, str]) -> str:
        return 'F15 ok.'

    def translate_out_mmu_response_release_all_channels(self, elements: dict[str, str]) -> str:
        return 'F18 ok'
    
    def translate_out_mmu_response_mark_active_channel(self, elements: dict[str, str]) -> str:
        channel_index = elements.get('channel', None)
        if channel_index == None:
            return 'F23 ok.'
        else:
            return f'F23 ok. chan {int(channel_index) + 1}.'
        
    def translate_out_mmu_response_clamp_channel(self, elements: dict[str, str]) -> str:
        channel_index = elements.get('channel', None)
        if channel_index == None:
            return 'F24 ok.'
        else:
            return f'F24 ok. chan {int(channel_index) + 1}.'
        
    def translate_out_mmu_response_release_channel(self, elements: dict[str, str]) -> str:
        channel_index = elements.get('channel', None)
        if channel_index == None:
            return 'F39 ok.'
        else:
            return f'F39 ok. FFS channel {int(channel_index) + 1} release.'
        
    def translate_out_mmu_response_halt_movement(self, elements: dict[str, str]) -> str:
        return 'F112 ok.'
    
    def translate_out_ij_response_get_status(self, elements: dict[str, str]) -> str:
        result = 'Z1 ok. '
        for key, value in elements:
            if key == 'command':
                continue
            result += f' {key}: {value}'
        return result