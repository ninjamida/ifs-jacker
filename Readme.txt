This is still beta. I have done some very limited testing of things like loading colors etc. No actual print yet. Use at your own risk.

Code is written for RP2040 Zero (and by extension should be compatible with Raspberry Pi Pico). Compatibility with other boards is not
guaranteed. It can likely be adapted to any board that supports MicroPython and has two cores with some degree of effort.

Upload all Python files in "src/", along with config.ini, to an RP2040 Zero with MicroPython installed. See config.ini.txt for info on
customizing config.ini.

Not that savvy and don't want to design your own build for this? I have a pre-designed build you can use; this is powered from the AD5X
itself and allows connecting two IFSes, optionally with a (always-on) 24V power header that can be used to connect a couple of rear-
panel fans. The provided config.ini is preconfigured for this build.

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
be inverted on some cables. This can be handled simply by crossing the A / B lines where they connect to the RS485 converter.