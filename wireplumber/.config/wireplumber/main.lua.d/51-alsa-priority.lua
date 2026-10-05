-- WirePlumber 0.4 form of the `monitor.alsa.rules` block in
-- ../wireplumber.conf.d/51-auto-switch.conf.
--
-- ALSA hands the Brio's IEC958 input 2008 and both the CalDigit dock input and
-- the built-in mic 2009, so on raw priority the webcam mic loses to whichever of
-- those enumerates first. With 51-no-persistent-defaults.lua discarding the saved
-- pick at every boot, raw priority is all there is — hence this rule.
--
-- Matched on the vendor/model prefix rather than the full node.name, which ends
-- in the unit's serial number.

table.insert (alsa_monitor.rules, {
  matches = {
    {
      { "node.name", "matches", "alsa_input.usb-046d_Brio_501*" },
    },
  },
  apply_properties = {
    ["priority.session"] = 2500,
  },
})
