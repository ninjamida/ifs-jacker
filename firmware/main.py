import ifs_splitter_system_consts as CONSTS
from ifs_splitter_logging import IFSSplitterLogging
from ifs_splitter_thread_comms import IFSSplitterThreadComms
from ifs_splitter_serial_comms import IFSSplitterSerialComms
from ifs_splitter_command_processor import IFSSplitterCommandProcessor
from ifs_splitter_console import IFSSplitterConsole
import _thread

# Bug: Doesn't come out of passthrough mode

def main():
    logging = IFSSplitterLogging()
    threadcomm = IFSSplitterThreadComms()
    serial = IFSSplitterSerialComms()
    processor = IFSSplitterCommandProcessor(serial, threadcomm, CONSTS.MAIN_THREADCOMM, CONSTS.CONSOLE_THREADCOMM)
    console = IFSSplitterConsole(threadcomm, CONSTS.CONSOLE_THREADCOMM, CONSTS.MAIN_THREADCOMM, logging)
    
    _thread.start_new_thread(console.execute, ())
    processor.execute()

    threadcomm.send(CONSTS.MAIN_THREADCOMM, "Z99")
    while processor.is_running:
        pass

main()