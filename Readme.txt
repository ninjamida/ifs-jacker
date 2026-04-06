IFS Jacker - IFS splitter for Flashforge AD5X

***
A huge amount of work went into this project. If you like it, please consider purchasing some of my paid models on Printables as
a way to support my work - feel free to think of it as making a donation that you also get a fun model in return for.

https://www.printables.com/@Trumble/store
***

This is still an early version. Use at your own risk.

At the time of writing this, I have done a few outside-print tests, and exactly two test prints - one with four colors on a single
IFS (but running through IFS Jacker, and on channels 5, 6, 7 and 8), and one eight-color print. Both of them completed without any
IFS Jacker problems (the 8 color print did run into a few issues arising from the 8-in-1 adapter I was using, but ultimately was
successful).

You will need zMod in order to use this. Support for this is not yet integrated into zMod, you will need to merge it into your
copy yourself. See here: https://github.com/ghzserg/z_ad5x/pull/8

Code is written for RP2040 Zero (and by extension should be compatible with Raspberry Pi Pico). Compatibility with other boards is not
guaranteed. It can likely be adapted to any board that supports MicroPython and has two cores with some degree of effort. One significant
thing to be aware of is that in comms.py, IJ_Comm_UART_EN_Multi uses direct writes via mem32[] to registers used to control GPIO pins.
This is done for fast switching of EN pins. The rest of the code will probably work as-is (though I cannot guarantee it) on other boards,
as long as they are dual-core (or more).

Upload all Python files in "src/", along with config.ini, to an RP2040 Zero with MicroPython installed. See config.ini.txt for info on
customizing config.ini.

Not that savvy and don't want to design your own build for this? I have a pre-designed build you can use; this is powered from the AD5X
itself and allows connecting two IFSes, optionally with a (always-on) 24V power header that can be used to connect a couple of rear-
panel fans. The provided config.ini is preconfigured for this build. You will need to be able to crimp cables in order to use this
design; soldering is not required.

https://www.printables.com/model/1644745-ifs-jacker-multi-ifs-adapter-for-zmodded-flashforg

To connect to the AD5X, you can either bypass the RS485 converter in the AD5X altogether (in which case use UART connection mode), or
you can connect via an RS485 adapter (use UART or UART-EN mode depending on whether the adapter has a dedicated EN pin; if it has DE
and RE, connect them both in parallel to the single configured EN pin).

To connect to IFSes, you will need one RS485 converter per IFS, no way around it. Unless you have ported IFS Jacker to a board with
more than two UARTs (or add your own PIO-based implementation for extra UARTs), you will need to use RS485 converters that have a
dedicated EN pin (or seperate DE and RE) - then, they can be wired in parallel to a single UART.

It may be wise to use a seperate power source if using four or more IFSes. For three or less, it should be fine to draw power from
the AD5X's IFS port.

The connector used for the IFSes is a four-pin Microfit 3.0. If you are using third-party cables, ensure that the pins connect as
expected - while the voltage / GND seem to be consistent across brands (at least between Flashforge and Bambu), the data lines may
be inverted on some cables. This can be handled simply by crossing the A / B lines where they connect to the RS485 converter. If
you are mounting one IFS on each side of your AD5X, I strongly recommend getting or making a longer cable (75cm to 1m) for the IFS
on the left side.

---

Are you developing an alternative firmware mod, or a Z-Mod plugin, and want to support IFS Jacker in it? All you need to do is talk
to it as if it's an IFS with 8 (or 12, or 16, etc) channels - just follow the logical extensions of existing commands / status codes.
To find out how many channels it has, check the extra "channel_count" param in the response to F13. (This does require enabling this
in IFS Jacker's settings.)

Extra commands (for status checks etc) are planned, but at the moment there are only two:

Z1 - This simply returns "Z1 ok." and does nothing else. The intent is to use it simply to confirm the presence of an IFS Jacker.
Z99 - This causes the IFS Jacker software to terminate (and the RP2040 to return to the MicroPython REPL interface).