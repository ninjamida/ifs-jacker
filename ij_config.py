from ij_core import IJ_Core
from ij_console import IJ_Console, console
from ij_comm_base import IJCI_Base, IJCI_Null
from ij_printer_base import IJP_Base, IJP_Null
from ij_mmu_base import IJM_Base, IJM_Null
import os

class IJ_Config_Loader:
    def load_modules(self):
        self.module_classes = {}

        for file in os.listdir('.'):
            if (file.startswith('ij_printer_') or file.startswith('ij_mmu_') or file.startswith('ij_comm_')) and file.endswith('.py'):
                module_name = file[:-3]
                module = __import__(module_name)
                for name, attr in module.__dict__.items():
                    if name.startswith('IJP_') or name.startswith('IJM_') or name.startswith('IJCI_'):
                        if isinstance(attr, type):
                            self.module_classes[name] = attr

    def parse_config_file(self) -> dict[str, dict[str, str]]:
        try:
            result = {'': {}}
            active_sec = result['']
            with open('ij_config.ini', 'rt') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('[') and line.endswith(']'):
                        sec_key = line[1:-1]
                        if not sec_key in result:
                            result[sec_key] = {}
                        active_sec = result[sec_key]
                    elif line != '':
                        line_split = line.split('=', 1)
                        if len(line_split) == 2:
                            active_sec[line_split[0].strip()] = line_split[1].strip()
                        else:
                            active_sec[line_split[0].strip()] = ''
            return result
        except Exception as e:
            print(f"!!! Loading config failed: {e}")
            return {}

    def load_config(self, core: IJ_Core):
        global console
        self.load_modules()

        file_data = self.parse_config_file()

        self.load_comm_interfaces(file_data)

        console = self.load_console_settings(file_data.get('Console', {}))
        core.printer = self.load_printer(file_data.get('Printer', {}))
        core.mmu = self.load_mmu(file_data.get('MMU', {}))

    def load_console_settings(self, console_sec: dict[str, str]) -> IJ_Console | None:
        if console_sec.get('enabled', 'True') == 'True':
            result = IJ_Console()
            if console_sec.get('read_only', 'False') == 'True':
                result.read_only = True
        else:
            result = None
        return result

    def load_printer(self, printer_data: dict[str, str]) -> IJP_Base:
        printer_type = printer_data.get('type', 'Null')
        printer_class = self.module_classes.get(f'IJP_{printer_type}', None)
        if printer_class and printer_class != IJP_Null:
            conn_id = printer_data.get('connection', 'Null')
            conn = self.comm_interfaces.get(conn_id)
            if conn is None:
                conn = IJCI_Null.make_from_config({})
            return printer_class.make_from_config(printer_data, conn)
        else:
            return IJP_Null.make_from_config({})

    def load_mmu(self, mmu_data: dict[str, str], key_prefix: str = '') -> IJM_Base:
        mmu_type = mmu_data.get(key_prefix + 'type', 'Null')
        mmu_class = self.module_classes.get(f'IJM_{mmu_type}', None)
        if mmu_class and mmu_class != IJM_Null:
            conn_id = mmu_data.get(key_prefix + 'connection', 'Null')
            conn = self.comm_interfaces.get(conn_id)
            if conn is None:
                conn = IJCI_Null.make_from_config({})
            return mmu_class.make_from_config(mmu_data, conn, key_prefix, self.load_mmu)
        else:
            return IJM_Null.make_from_config({})

    def load_comm_interfaces(self, file_data: dict[str, dict[str, str]]):
        self.comm_interfaces = {}

        for sec_key, sec_value in file_data.items():
            if sec_key.startswith('Comm_'):
                interface_name = sec_key[5:]
                interface_type = sec_value.get('type', 'Null')
                interface_class = self.module_classes.get(f'IJCI_{interface_type}', None)
                if interface_class:
                    self.comm_interfaces[interface_name] = interface_class.make_from_config(sec_value)
                else:
                    self.comm_interfaces[interface_name] = IJCI_Null.make_from_config({})
    
    def get_comm_interface(self, interface_name: str) -> IJCI_Base:
        if interface_name in self.comm_interfaces:
            return self.comm_interfaces[interface_name]
        
        for name in self.comm_interfaces.keys():
            if interface_name.split(':', 1)[0] == name:
                parent_interface = self.comm_interfaces[name]
                if getattr(parent_interface, 'make_child', None):
                    name_params = interface_name.split(':')[1:]
                    result = parent_interface.make_child(*name_params)
                    self.comm_interfaces[interface_name] = result
                    return result
                else:
                    return parent_interface
                
        return IJCI_Base() # Null
                
