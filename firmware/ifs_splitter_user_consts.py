# Wiring settings
PRINTER_UART = 1
PRINTER_TX_PIN = 4
PRINTER_RX_PIN = 5
PRINTER_EN_PIN = 3

IFS_UART = 0
IFS_TX_PIN = 0
IFS_RX_PIN = 1
IFS_EN_PINS = [8, 9] # To add more IFSes, add their EN pin number to this line. Order-sensitive (ie: first entry is IFS 0 etc).
                     # The number of IFSes you can add - software-wise at least - is limited only by the number of GPIO pins.

# Logging settings
LOGGING = True # Whether to enable saving logs to file
LOG_FILE_MAX_SIZE = 128 * 1024 # Maximum size of a single log file
LOG_MAX_OLD_FILES = 3 # Maximum number of old log files to keep

# Misc settings / consts
INITIAL_PASSTHROUGH_TARGET = -1  # Which IFS channel to initially be in passthrough mode to. -1 for splitter mode.