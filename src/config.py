from util import load_ini_file
from console import get_console
from core import IJ_Core
from p_dummy import IJP_Dummy
from peripheral import load_peripheral
import comm, gc

STANDARD_COMM_GENERATION_TYPES = [comm.IJ_Comm_UART, comm.IJ_Comm_UART_EN]

def load_config(core: IJ_Core, comm_mgr: comm.IJ_Comm_Manager):
    ini_data = load_ini_file('config.ini')
    console = get_console()

    core_data = ini_data.get('core', {})
    core.printer_connected_timeout = int(float(core_data.get('timeout', 3)) * 1000)
    core.include_channel_count_in_status = core_data.get('include_channel_count_in_status', 'true') == 'true'
    old_include_peripherals_in_status = core_data.get('include_peripherals_in_status', None)
    if old_include_peripherals_in_status is not None:
        if old_include_peripherals_in_status == 'true':
            core.peripherals_in_status_count = -1
        else:
            core.peripherals_in_status_count = 0
    else:
        core.peripherals_in_status_count = int(core_data.get('peripherals_in_status', -1))
    core.mmu_response_timeout = int(float(core_data.get('mmu_timeout', 0.065)) * 1000)
    force_present_channels = [item.strip() for item in core_data.get('force_present_channels', '').split(',')]
    force_absent_channels = [item.strip() for item in core_data.get('force_absent_channels', '').split(',')]
    if len(force_absent_channels) > 1 or force_absent_channels[0] != '':
        mask = 0
        for i in [int(channel) for channel in force_absent_channels]:
            mask |= 1 << i-1
        core.force_absent_mask = ~mask
    if len(force_present_channels) > 1 or force_present_channels[0] != '':
        mask = 0
        for i in [int(channel) for channel in force_present_channels]:
            mask |= 1 << i-1
        core.force_present_mask = mask & core.force_absent_mask

    console_data = ini_data.get('console', {})
    console.exclude_categories = [item.strip() for item in console_data.get('exclude_categories', '').split(',')]
    if len(console.exclude_categories) == 1 and console.exclude_categories[0] == '':
        console.exclude_categories = ['silent']
    console.include_categories = [item.strip() for item in console_data.get('include_categories', '').split(',')]
    if len(console.include_categories) == 1 and console.include_categories[0] == '':
        console.include_categories = []

    multi_connections: dict = {}
    all_comms: list = []

    for multi_key in ini_data.keys():
        if multi_key.startswith('uart_multi_') and len(multi_key) > 11:
            new_id = multi_key[11:]
            console.print(f'Loading UART multi-connection {new_id}', 'config')
            new_multi_comm = comm.IJ_Comm_UART_EN_Multi.make_from_config(ini_data[multi_key])
            multi_connections[new_id] = new_multi_comm
            all_comms.append(new_multi_comm)

    printer_data = ini_data.get('printer', None)
    if printer_data:
        console.print(f'Loading printer', 'config')
        core.printer_comm = get_comm(printer_data, multi_connections)
        all_comms.append(core.printer_comm)

    mmu_index = 0
    while f'mmu_{mmu_index}' in ini_data.keys():
        console.print(f'Loading MMU {mmu_index}', 'config')
        mmu_data = ini_data[f'mmu_{mmu_index}']
        new_comm = get_comm(mmu_data, multi_connections)
        core.mmu_comms.append(new_comm)
        all_comms.append(new_comm)
        mmu_index += 1

    comm_mgr.comm_list = all_comms

    peripherals = load_peripherals(ini_data, all_comms)
    core.peripherals = peripherals.copy()

    for this_comm in all_comms:
        this_comm.initialize()

    for this_peripheral in peripherals:
        this_peripheral.initialize()
    gc.collect()

def get_comm(data: dict[str, str], multi_connections: dict):
    multi_id = data.get('multi_id', '')
    multi_parent = multi_connections.get(multi_id, None)
    if multi_parent:
        return multi_parent.make_child(data)
    elif multi_id != '':
        raise Exception(f'Invalid multi ID "{multi_id}"')

    comm_type = f'ij_comm_{data.get('comm', '')}'
    for standard_type in STANDARD_COMM_GENERATION_TYPES:
        if standard_type.__name__.lower() == comm_type:
            return standard_type.make_from_config(data)

    raise Exception(f'Invalid comm type "{comm_type}"')

def load_peripherals(ini_data: dict[str, dict[str, str]], all_comms: list[comm._IJ_Comm_Abstract]) -> list:
    console = get_console()

    console.print('Loading peripherals', 'config')
    highest_index = -1
    for sec_name in ini_data.keys():
        if sec_name.startswith('peripheral_'):
            try:
                this_index = int(sec_name[11:])
                highest_index = max(highest_index, this_index)
            except:
                pass

    result = []
    for i in range(highest_index + 1):
        if f'peripheral_{i}' in ini_data:
            console.print(f'Loading peripheral {i}', 'config')
            try:
                peripheral_sec = ini_data[f'peripheral_{i}']
                new_peripheral = load_peripheral(i, peripheral_sec, all_comms)

                result.append(new_peripheral)
            except KeyboardInterrupt:
                raise        
            except Exception as e:
                new_peripheral = IJP_Dummy()
                new_peripheral.identifier = "Failed to load"
                result.append(new_peripheral)
                console.print_exception(e, 'config')
        else:
            new_peripheral = IJP_Dummy()
            new_peripheral.identifier = "Placeholder dummy"
            result.append(new_peripheral)

    return result
