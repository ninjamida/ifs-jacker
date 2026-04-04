SCRIPT_IDENTIFIER = 'IFS Jacker'
SCRIPT_AUTHOR = 'Namida Verasche (Trumble)'
SCRIPT_VERSION = '2.0.0'

from core import IJ_Core
from comm import IJ_Comm_Manager
from console import get_console
from config import load_config
import time

def main():
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

        console.print('Starting comm manager on second thread', 'info')
        console.flush()
        comm.start_thread()

        console.print('Starting core on primary thread', 'info')
        console.flush()
        core.run()
    except Exception as e:
        console.print_exception(e, 'startup')
        console.flush()

    console.print('Core terminated', 'info')
    console.flush()
    
    if comm.started and not comm.finished:
        console.print('Waiting for comm manager to exit', 'info')
        time.sleep_ms(300) # In case shutdown was from a Z99 command, so that the response has time to send
        comm.terminate = True
        console.flush()
        while not comm.finished:
            pass

    console.print('IFS Jacker terminated', '')
    console.flush()

main()