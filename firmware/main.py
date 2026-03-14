import ifs_jacker_system_consts as CONSTS
from ifs_jacker_config import IFSJackerConfig
from ifs_jacker_logging import IFSJackerLogging
from ifs_jacker_thread_comms import IFSJackerThreadComms
from ifs_jacker_serial_comms import IFSJackerSerialComms
from ifs_jacker_command_processor import IFSJackerCommandProcessor
from ifs_jacker_console import IFSJackerConsole
import _thread, machine

reboot_flag = False

def execute():
    global reboot_flag

    config = IFSJackerConfig()
    config.load_file()

    logging = IFSJackerLogging(config)
    threadcomm = IFSJackerThreadComms(config)
    serial = IFSJackerSerialComms(config)
    processor = IFSJackerCommandProcessor(config, serial, threadcomm, CONSTS.MAIN_THREADCOMM, CONSTS.CONSOLE_THREADCOMM)
    console = IFSJackerConsole(config, threadcomm, CONSTS.CONSOLE_THREADCOMM, CONSTS.MAIN_THREADCOMM, logging)
    
    _thread.start_new_thread(console.execute, ())
    processor.execute()

    threadcomm.send(CONSTS.MAIN_THREADCOMM, "Z99")
    threadcomm.send(CONSTS.CONSOLE_THREADCOMM, "Z99")
    while processor.is_running or console.is_running:
        pass

    logging.flush_logs()
    reboot_flag = processor.reboot_flag

def main():
    execute()
    if reboot_flag:
        machine.reset()

main()