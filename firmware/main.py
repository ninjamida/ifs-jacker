import ifs_splitter_system_consts as CONSTS
from ifs_splitter_config import IFSSplitterConfig
from ifs_splitter_logging import IFSSplitterLogging
from ifs_splitter_thread_comms import IFSSplitterThreadComms
from ifs_splitter_serial_comms import IFSSplitterSerialComms
from ifs_splitter_command_processor import IFSSplitterCommandProcessor
from ifs_splitter_console import IFSSplitterConsole
import _thread

def main():
    config = IFSSplitterConfig()
    config.load_file()

    logging = IFSSplitterLogging(config)
    threadcomm = IFSSplitterThreadComms(config)
    serial = IFSSplitterSerialComms(config)
    processor = IFSSplitterCommandProcessor(config, serial, threadcomm, CONSTS.MAIN_THREADCOMM, CONSTS.CONSOLE_THREADCOMM)
    console = IFSSplitterConsole(config, threadcomm, CONSTS.CONSOLE_THREADCOMM, CONSTS.MAIN_THREADCOMM, logging)
    
    _thread.start_new_thread(console.execute, ())
    processor.execute()

    threadcomm.send(CONSTS.MAIN_THREADCOMM, "Z99")
    threadcomm.send(CONSTS.CONSOLE_THREADCOMM, "Z99")
    while processor.is_running or console.is_running:
        pass

    logging.flush_logs()

main()