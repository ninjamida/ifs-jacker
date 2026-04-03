SCRIPT_IDENTIFIER = 'IFS Jacker'
SCRIPT_AUTHOR = 'Namida Verasche (Trumble)'
SCRIPT_VERSION = '1.0.0'

import sys, io

def get_traceback_string(e: Exception) -> list[str]:
    buf = io.StringIO()
    sys.print_exception(e, buf)
    return buf.getvalue().splitlines()

def decode_valid_bytes(data: bytes) -> str:
    return str(bytes(b for b in data if b < 128), 'utf-8')