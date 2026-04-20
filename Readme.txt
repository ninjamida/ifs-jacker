IFS Jacker - IFS splitter for Flashforge AD5X

***
A huge amount of work went into this project. If you like it, please consider
purchasing some of my paid models on Printables as a way to support my work -
feel free to think of it as making a donation that you also get a fun model in
return for.

https://www.printables.com/@Trumble/store
***

At this time, IFS Jacker has had limited testing. Build and use at your own
risk. With that being said, I've had my IFS Jacker attached to my printer for
a couple of weeks now and all IFS functionality has worked fine.

In order to use an IFS Jacker, you will need to have Z-Mod, and you will need to
be using GuppyScreen or HelixScreen (or no screen) - the native screen will not
properly communicate with an IFS Jacker.

You will also either need to set a "color_limit" param in your [zmod_ifs]
configuration section (set it to the number of colors you have available), or
install the IFS Jacker plugin. At the time of writing, the IFS Jacker plugin
must manually be added to zMod's plugin list. To do this, add the following to
your user.moonraker.conf file then restart your printer:

[update_manager ifs_jacker]
type: git_repo
channel: stable
path: /root/printer_data/config/mod_data/plugins/ifs_jacker
origin: https://github.com/ninjamida/ifs_jacker_plugin.git
is_system_service: False
primary_branch: master

Once installed, run "ENABLE_PLUGIN NAME=ifs_jacker" to enable it. Whenever you
update the IFS Jacker plugin, if it is enabled, you should re-run the enable
command afterwards (you do not need to run a disable command first).

---

Code is written for RP2040 Zero (and by extension should be compatible with
Raspberry Pi Pico). Compatibility with other boards is not guaranteed. It can
likely be adapted to any board that supports MicroPython and has two cores with
some degree of effort. One significant thing to be aware of is that in comms.py,
IJ_Comm_UART_EN_Multi uses direct writes via mem32[] to registers used to
control GPIO pins. This is done for fast switching of EN pins. The rest of the
code will probably work as-is (though I cannot guarantee it) on other boards,
as long as they are dual-core (or more).

Upload all Python files in "src/", along with config.ini, to an RP2040 Zero with
MicroPython installed. See config.ini.txt for info on customizing config.ini.

Not that savvy and don't want to design your own build for this? I have a pre-
designed build you can use; this is powered from the AD5X itself and allows
connecting two IFSes, optionally with a (always-on) 24V or 5V power header that
can be used to connect a couple of rear-panel fans. The provided config.ini is
preconfigured for this build. You will need to be able to crimp cables in order
to use this design; soldering is not required. If you are using this build,
the included config.ini file is already set up for it.

https://www.printables.com/model/1644745-ifs-jacker

To connect to the AD5X, you can either bypass the RS485 converter in the AD5X
altogether (in which case use UART connection mode), or you can connect via an
RS485 adapter (use UART or UART-EN mode depending on whether the adapter has a
dedicated EN pin; if it has DE and RE, connect them both in parallel to the
single configured EN pin).

To connect to IFSes, you will need one RS485 converter per IFS, no way around
it. Unless you have ported IFS Jacker to a board with more than two UARTs (or
add your own PIO-based implementation for extra UARTs), you will need to use
RS485 converters that have a dedicated EN pin (or seperate DE and RE) - then,
they can be wired in parallel to a single UART.

It may be wise to use a seperate power source if using four or more IFSes. For
three or less, it should be fine to draw power from the AD5X's IFS port.

The connector used for the IFSes is a four-pin Microfit 3.0. If you are using
third-party cables, ensure that the pins connect as expected - while the voltage
/ GND seem to be consistent across brands (at least between Flashforge and
Bambu), the data lines may be inverted on some cables. This can be handled
simply by crossing the A / B lines where they connect to the RS485 converter. If
you are mounting one IFS on each side of your AD5X, I strongly recommend getting
or making a longer cable (75cm to 1m) for the IFS on the left side.

---

Are you developing an alternative firmware mod, or a Z-Mod plugin, and want to
support IFS Jacker in it? All you need to do is talk to it as if it's an IFS
with 8 (or 12, or 16, etc) channels - just follow the logical extensions of
existing commands / status codes. To find out how many channels it has, check
the extra "channel_count" param in the response to F13. (This does require
enabling this in IFS Jacker's settings.)

A few extra commands are also available. Sample responses are also provided. Any
newlines in these responses are purely for readability; responses are sent as a
single line of text.

Z1 - This command does nothing but respond. It can be used to confirm the
     presence of an IFS Jacker. Z2 can then be used to get more info. (Of course
     you could also just directly use Z2; but Z1 was implemented earlier.)
 Response: Z1 ok.
  
Z2 - Get information on IFS Jacker software and configuration.
 Response: Z2 ok. software: "IFS Jacker" version: "2.1.0" author: "Namida
           Verasche (Trumble)" ifs_count: 2 channel_count: 8 peripheral_count: 0

Z3 - Get the identifiers of all peripherals.
 Response: Z3 ok. peripheral_0: "Digital Pin 12 Input" peripheral_1: "Dummy"
     If there are no peripherals, it will just respond "Z3 ok."
     
Z4 - Get the status codes of all peripherals.
 Response: Z4 ok. peripheral_0: 1
     If there are no peripherals, or all peripherals are configured not to
     report in Z4, it will just respond "Z4 ok."
     
Z5 - Send a command to a peripheral. F, C, L and S params are passed on.
 Response: Z5 ok. F3 peripheral ok. Pin set high
       or: Z5 ok. Invalid peripheral index 5
     
Z99 - This causes the IFS Jacker software to terminate (and the RP2040 to return
      to the MicroPython REPL interface).