SCRIPT_IDENTIFIER = 'IFS Jacker'
SCRIPT_AUTHOR = 'Namida Verasche (Trumble)'
SCRIPT_VERSION = '1.0.0'

import sys, io

def get_traceback_string(e: Exception) -> list[str]:
    buf = io.StringIO()
    sys.print_exception(e, buf)
    return buf.getvalue().splitlines()