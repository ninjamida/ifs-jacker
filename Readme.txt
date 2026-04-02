This is still a work in progress. It is NOT ready for use yet.

Code is written for RP2040 Zero (and by extension should be compatible with Raspberry Pi Pico). Compatibility with other boards is not
guaranteed. It can likely be adapted to any board that supports MicroPython with some degree of effort.

Code is written to be expandable to support other printers / MMUs, but I have no plans at this stage to actually add support for any.

When attaching the MicroFit connectors to the MAX3485 boards; if you are using non-Flashforge IFS cables, you may need to swap the A
and B lines at some point, as some cables also swap these. Bambu cables have them swapped; I cannot comment on Creality or Anycubic.