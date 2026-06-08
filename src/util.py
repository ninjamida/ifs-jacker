import sys, io

SCRIPT_IDENTIFIER = 'IFS Jacker'
SCRIPT_AUTHOR = 'Namida Verasche (Trumble)'
SCRIPT_VERSION = '3.1.0'

def get_traceback_string(e: Exception) -> list[str]:
    buf = io.StringIO()
    sys.print_exception(e, buf)
    return buf.getvalue().splitlines()

def decode_valid_bytes(data: bytes) -> str:
    return str(bytes(b for b in data if b < 128), 'utf-8')

def load_ini_file(filename: str) -> dict[str, dict[str, str]]:
    result = {'': {}}
    active_sec = result['']
    with open(filename, 'rt') as f:
        for line in f:
            line = line.split(';', 1)[0].strip()
            if line.startswith('#'):
                continue
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