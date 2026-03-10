import ifs_splitter_system_consts as CONSTS

class IFSSplitterConfig:
    CONFIG_PARAMS = {
        'printer_uart': 'int',
        'printer_tx_pin': 'int',
        'printer_rx_pin': 'int',
        'printer_en_pin': 'int',
        'ifs_uart': 'int',
        'ifs_tx_pin': 'int',
        'ifs_rx_pin': 'int',
        'ifs_en_pins': 'list-int',
        'logging': 'bool',
        'log_file_max_size': 'int',
        'initial_passthrough_target': 'int'
    } # Valid types: int, list-int, bool, str

    def __init__(self):
        for attr in self.CONFIG_PARAMS.keys():
            setattr(self, attr, None)

        self.logging = False
        self.log_max_file_size = 128 * 1024
        self.initial_passthrough_target = 0

    def get_missing_options(self):
        failed_vars = []
        for attr in self.CONFIG_PARAMS.keys():
            if getattr(self, attr) == None:
                failed_vars += [attr]
        return failed_vars
    
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
                        ini_dic[elements[0].strip().lower()] = elements[1].strip()
            for key, value in ini_dic.items():
                setting_type = self.CONFIG_PARAMS.get(key, None)
                set_value = None
                print(f"{key}:{value}:{setting_type}")
                if setting_type == 'int':
                    try:
                        set_value = int(value)
                    except (ValueError, TypeError):
                        pass
                if setting_type == 'bool':
                    try:
                        set_value = (value.lower() == 'true') or int(value) != 0
                    except (ValueError, TypeError):
                        pass
                if setting_type == 'str':
                    set_value = value
                if setting_type == 'list-int':
                    try:
                        set_value = [int(element.strip()) for element in value.split(',')]
                    except (ValueError, TypeError):
                        pass
                if set_value != None:
                    setattr(self, key, set_value)
        except OSError:
            pass

    def save_file(self):
        need_to_save = list(self.CONFIG_PARAMS.keys())
        try:
            with open(CONSTS.USER_SETTINGS_FILENAME, 'r') as f:
                lines = f.read()
        except:
            lines = []

        with open(CONSTS.USER_SETTINGS_FILENAME, 'w') as f:
            for line in lines:
                line = line.strip()
                for key in need_to_save:
                    if line.startswith(key + '='):
                        attr = getattr(self, key)
                        if self.CONFIG_PARAMS[key].startswith('list'):
                            new_value = ','.join([str(item) for item in attr])
                        else:
                            new_value = str(attr)
                        line = line[:len(key) + 1] + new_value
                        need_to_save.remove(key)
                print(line, file=f)
            if len(need_to_save) > 0:
                if len(lines) > 0:
                    print('', file=f)
                for key in need_to_save:
                    attr = getattr(self, key)
                    if self.CONFIG_PARAMS[key].startswith('list'):
                        new_value = ','.join([str(item) for item in attr])
                    else:
                        new_value = str(attr)
                    line = key.upper() + '=' + new_value
                    print(line, file=f)
