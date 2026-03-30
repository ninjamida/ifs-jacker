import ifs_jacker_system_consts as CONSTS

class IFSJackerConfig:
    CONFIG_PARAMS = {
        'printer_uart': 'int',
        'printer_tx_pin': 'int',
        'printer_rx_pin': 'int',
        'printer_en_pin': 'int',
        'ifs_uart': 'int',
        'ifs_tx_pin': 'int',
        'ifs_rx_pin': 'int',
        'ifs_en_pins': 'list-int',
        'initial_passthrough_target': 'int'
    } # Valid types: int, list-int, bool, str

    CONFIG_PARAMS_HUMAN_FRIENDLY = {
        'printer_uart': 'UART index for connection to printer',
        'printer_tx_pin': 'TX pin for connection to printer',
        'printer_rx_pin': 'RX pin for connection to printer',
        'printer_en_pin': 'EN pin for connection to printer',
        'ifs_uart': 'UART index for connection to IFSes',
        'ifs_tx_pin': 'TX pin for connection to IFSes',
        'ifs_rx_pin': 'RX pin for connection to IFSes',
        'ifs_en_pins': 'EN pins for connections to IFSes (comma-seperated)',
        'initial_passthrough_target': 'Passthrough mode target IFS index at startup (-1 to start in splitter mode)'
    }

    NEED_REBOOT_OPTIONS = [
        'printer_uart', 'printer_tx_pin', 'printer_rx_pin',
        'ifs_uart', 'ifs_tx_pin', 'ifs_rx_pin', 'ifs_en_pins'
    ]

    def __init__(self):
        for attr in self.CONFIG_PARAMS.keys():
            setattr(self, attr, None)

        self.initial_passthrough_target = 0

    def get_missing_options(self):
        failed_vars = []
        for attr in self.CONFIG_PARAMS.keys():
            if getattr(self, attr) == None:
                failed_vars += [attr]
        return failed_vars
    
    def is_reboot_needed_after_changing(self, option_name):
        return option_name.lower() in self.NEED_REBOOT_OPTIONS
    
    def configure_via_console(self, missing_only = True):
        print("IFS Jacker configuration")
        for attr in self.CONFIG_PARAMS.keys():
            complete = False
            while not complete:
                existing_val = getattr(self, attr)
                if existing_val == None or not missing_only:
                    text = self.CONFIG_PARAMS_HUMAN_FRIENDLY.get(attr, f'Config option "{attr}"')
                    if existing_val != None:
                        text += f' (current: {existing_val})'
                    text += ': '
                    new_val = input(text)
                    complete = self.set_from_string(attr, new_val)
                    if not complete:
                        print('Invalid input')
        self.save_file()
    
    def set_from_string(self, option, value):
        option = option.lower()
        setting_type = self.CONFIG_PARAMS.get(option, None)
        if setting_type != None:
            set_value = None
            if setting_type == 'int':
                try:
                    set_value = int(value)
                except (ValueError, TypeError):
                    pass
            if setting_type == 'bool':
                try:
                    set_value = (value.lower() == 'true') or int(value) != 0
                except (ValueError, TypeError):
                    set_value = False
            if setting_type == 'str':
                set_value = value
            if setting_type == 'list-int':
                try:
                    set_value = [int(element.strip()) for element in value.split(',')]
                except (ValueError, TypeError):
                    pass
            if set_value != None:
                setattr(self, option, set_value)
                return True
        return False

    def get_all_settings(self):
        results = []
        for key in self.CONFIG_PARAMS.keys():
            results.append(f"{key}: {getattr(self, key)}")
        return ' '.join(results)
    
    def load_file(self):
        ini_dic = {}
        try:
            with open(CONSTS.USER_SETTINGS_FILENAME, 'rt') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(';'):
                        continue
                    elements = line.split('=', 1)
                    if len(elements) == 2:
                        ini_dic[elements[0].strip()] = elements[1].strip()
            for key, value in ini_dic.items():
                self.set_from_string(key, value)
        except OSError as e:
            print(f"Config could not be loaded: {e}")

    def save_file(self):
        need_to_save = list(self.CONFIG_PARAMS.keys())
        try:
            with open(CONSTS.USER_SETTINGS_FILENAME, 'r') as f:
                lines = f.readlines()
        except:
            lines = []

        with open(CONSTS.USER_SETTINGS_FILENAME, 'w') as f:
            for line in lines:
                line = line.strip()
                for key in need_to_save:
                    if line.lower().startswith(key.lower() + '='):
                        attr = getattr(self, key)
                        if self.CONFIG_PARAMS[key].startswith('list'):
                            new_value = ','.join([str(item) for item in attr])
                        else:
                            new_value = str(attr)
                        line = line[:len(key) + 1] + new_value
                        need_to_save.remove(key)
                if not line.endswith('\n'):
                    line += '\n'
                f.write(line)
            if len(need_to_save) > 0:
                if len(lines) > 0:
                    print('', file=f)
                for key in need_to_save:
                    attr = getattr(self, key)
                    if self.CONFIG_PARAMS[key].startswith('list'):
                        new_value = ','.join([str(item) for item in attr])
                    else:
                        new_value = str(attr)
                    line = key.upper() + '=' + new_value + '\n'
                    f.write(line)
