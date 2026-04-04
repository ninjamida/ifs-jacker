from ij_comm_base import IJCI_Base
from ij_mmu_base import IJM_Text_Based

class IJM_IFS(IJM_Text_Based):
    def __init__(self, connection: IJCI_Base):
        super().__init__(connection)
        self.friendly_name = "Flashforge IFS"
        self.ignore_invalid_characters = True

    def get_channel_count(self) -> int:
        return 4
    
    @staticmethod
    def make_from_config(config_data: dict[str, str], connection: IJCI_Base, key_prefix: str = '', load_mmu_func = None) -> IJM_IFS:
        return IJM_IFS(connection)
    
    def translate_in_F10(self, elements: list[str]) -> dict[str, str]:
        return {
            'command': 'mmu_response_insert_filament',
            'channel': str(int(elements[4]) - 1)
            }
    
    def translate_in_F11(self, elements: list[str]) -> dict[str, str]:
        return {
            'command': 'mmu_response_withdraw_filament',
            'channel': str(int(elements[4]) - 1)
            }
    
    def translate_in_F13(self, elements: list[str]) -> dict[str, str]:
        result = {'command': 'mmu_response_get_status'}
        i = 1
        ffs_state = 5
        silk_state = 0
        chan_state = 0
        insert_state = 0
        stall_state = 0
        while i + 1 < len(elements):
            if elements[i] == 'FFS_state:':
                i += 1
                ffs_state = int(elements[i])
            elif elements[i] == 'silk_state:':
                i += 1
                silk_state = int(elements[i])
            elif elements[i] == 'chan:':
                i += 1
                chan_state = int(elements[i])
            elif elements[i] == 'ffs_channels_insert:':
                i += 1
                insert_state = int(elements[i])
            elif elements[i] == 'stall_state:':
                i += 1
                stall_state = int(elements[i])
            i += 1

        if ffs_state == 3:
            result['global_state'] = 'querying'
        elif ffs_state == 127:
            result['global_state'] = 'driver_error'
        else:
            result['global_state'] = 'ok'

        result['active_channel'] = str(chan_state)

        for i in range(self.get_channel_count()):
            bitmask = 1 << i
            channel_prefix = f'channel_{i}_'
            result[channel_prefix + 'present'] = str((silk_state & bitmask) != 0)
            result[channel_prefix + 'need_insert'] = str((insert_state & bitmask) != 0)
            result[channel_prefix + 'stall'] = str((stall_state & bitmask) != 0)
            channel_state = 'ok'
            if ffs_state == (i * 11) + 7:
                channel_state = 'clamped'
            elif ffs_state == (i * 11) + 11:
                channel_state = 'inserting'
            elif ffs_state == (i * 11) + 12:
                channel_state = 'released'
            elif ffs_state == (i * 11) + 15:
                channel_state = 'withdrawing'
            result[channel_prefix + 'state'] = channel_state

        result['channel_count'] = str(self.get_channel_count())

        return result

    def translate_in_F15(self, elements: list[str]) -> dict[str, str]:
        return {'command': 'mmu_response_reset_drivers'}
    
    def translate_in_F18(self, elements: list[str]) -> dict[str, str]:
        return {'command': 'mmu_response_release_all_channels'}
    
    def translate_in_F23(self, elements: list[str]) -> dict[str, str]:
        return {
            'command': 'mmu_response_mark_active_channel',
            'channel': str(int(elements[3][:-1]) - 1)
        }
    
    def translate_in_F24(self, elements: list[str]) -> dict[str, str]:
        return {
            'command': 'mmu_response_clamp_channel',
            'channel': str(int(elements[3][:-1]) - 1)
        }
    
    def translate_in_F39(self, elements: list[str]) -> dict[str, str]:
        return {
            'command': 'mmu_response_release_channel',
            'channel': str(int(elements[4]) - 1)
        }

    def translate_in_F112(self, elements: list[str]) -> dict[str, str]:
        return {'command': 'mmu_response_halt_movement'}
    
    def translate_out_mmu_insert_filament(self, command: dict[str, str]) -> str | None:
        return f"F10 C{int(command['channel']) + 1} L{command['length']} S{command['speed']}\r\n"
    
    def translate_out_mmu_withdraw_filament(self, command: dict[str, str]) -> str | None:
        return f"F11 C{int(command['channel']) + 1} L{command['length']} S{command['speed']}\r\n"
    
    def translate_out_mmu_get_status(self, command: dict[str, str]) -> str | None:
        return "F13\r\n"
    
    def translate_out_mmu_reset_drivers(self, command: dict[str, str]) -> str | None:
        return "F15 C\r\n"
    
    def translate_out_mmu_release_all_channels(self, command: dict[str, str]) -> str | None:
        return "F18\r\n"
    
    def translate_out_mmu_mark_active_channel(self, command: dict[str, str]) -> str | None:
        return f"F23 C{int(command['channel']) + 1}\r\n"
    
    def translate_out_mmu_clamp_channel(self, command: dict[str, str]) -> str | None:
        return f"F24 C{int(command['channel']) + 1}\r\n"
    
    def translate_out_mmu_release_channel(self, command: dict[str, str]) -> str | None:
        return f"F39 C{int(command['channel']) + 1}\r\n"
    
    def translate_out_mmu_halt_movement(self, command: dict[str, str]) -> str | None:
        return "F112\r\n"