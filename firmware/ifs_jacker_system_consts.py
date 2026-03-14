# Software info
SCRIPT_IDENTIFIER = 'IFS Jacker'
SCRIPT_AUTHOR = 'ninjamida'
SCRIPT_VERSION = '0.10'
SCRIPT_HARDWARE = 'RP2040 Zero'

# Console settings
TIMESTAMP_DIGITS = 10
CONSOLE_RESPONSE_TIMEOUT = 1 # Timeout to wait for response after sending a command from console
CONSOLE_EXTRA_RESPONSE_TIMEOUT = 0.1 # Timeout to wait after console response for further responses
CONSOLE_INPUT_PREFIX = "  Command:" # Length should equal TIMESTAMP_DIGITS

# Logging settings
LOG_FLUSH_TIME = 15 # Flush logs if no new data for this long
LOG_FLUSH_COUNT = 32 # FLush logs if this many unflushed logs are reached

# Threadcomm settings
THREADCOMM_CHANNELS = 2
MAIN_THREADCOMM = 0
CONSOLE_THREADCOMM = 1

# Serial settings
UART_BAUD = 115200
UART_BITS = 8
UART_PARITY = None
UART_STOP_BITS = 1
RECEIVE_START_TIMEOUT = 0.2
INTER_CHAR_TIMEOUT = 0.05
PASSTHROUGH_MINIMUM_SILENCE_BEFORE_Z_COMMAND = 3 # In passthrough mode, Z commands will only be captured if
                                                 # it has been this many seconds since the last data other than
                                                 # a Z command. This does not apply on first poweron, or to
                                                 # Z commands received from the console.

# Misc settings / consts
IFS_FFS_STATE_OK = 5
USER_SETTINGS_FILENAME = "ifs_jacker_config.ini"
