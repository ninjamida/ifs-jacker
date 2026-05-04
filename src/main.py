# IFS Jacker code by Namida Verasche
# https://github.com/ninjamida/ifs-jacker
# Version info in util.py

from core import IJ_Core
from comm import IJ_Comm_Manager
from console import get_console
from config import load_config
import machine
from util import SCRIPT_IDENTIFIER, SCRIPT_VERSION, SCRIPT_AUTHOR

def main():
    machine.freq(200000000)
    console = get_console()

    console.print(f'{SCRIPT_IDENTIFIER} version {SCRIPT_VERSION}', '')
    console.print(f'Author: {SCRIPT_AUTHOR}', '')
    console.print('', '')

    try:
        core = IJ_Core()
        comm = IJ_Comm_Manager()
        core.comm = comm
        comm.core = core

        load_config(core, comm)

        console.print('Starting core', 'info')
        console.flush()
        core.run()    
    except Exception as e:
        if not isinstance(e, KeyboardInterrupt):
            console.print_exception(e, 'startup')
            console.flush()

    console.print('IFS Jacker terminated', 'info')
    console.flush()

main()