-- WirePlumber 0.4 port of the `monitor.bluez.rules` block in
-- ../wireplumber.conf.d/51-auto-switch.conf. See that file for the 0.5 form;
-- 0.4 ignores wireplumber.conf.d/ and 0.5 ignores this directory, so both
-- versions of the package can be stowed on either machine.
--
-- Bluetooth sinks come up at 1010, one point above the laptop speakers and the
-- CalDigit dock (both 1009 here — ALSA gives USB and PCI analog stereo the same
-- number). One point is enough to win the race but not enough to survive anything
-- that nudges the others, so lift them clear of both.
--
-- table.insert rather than `bluez_monitor.rules = {...}`: 50-bluez-config.lua
-- assigns that table, and a plain assignment here would drop its defaults.

table.insert (bluez_monitor.rules, {
  matches = {
    {
      { "node.name", "matches", "bluez_output.*" },
    },
  },
  apply_properties = {
    ["priority.session"] = 1500,
  },
})
