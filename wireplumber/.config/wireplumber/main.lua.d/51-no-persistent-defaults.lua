-- WirePlumber 0.4 port of `node.restore-default-targets = false` in
-- ../wireplumber.conf.d/51-auto-switch.conf: don't carry the chosen sink/source
-- across restarts, so a fresh boot starts on raw priority.
--
-- Only the persistence half ports. The 0.5 package also replaces default-node
-- selection with scripts/sticky-default-node.lua, which has no counterpart here:
-- in 0.4 the selection lives in the `default-nodes` C module loaded below by
-- device_defaults.enable(), not in a Lua hook chain, so there is nothing to
-- override. The consequence on 0.4 is that a manual pick — GNOME Settings or
-- `wpctl set-default` — writes default.configured.<type> and holds for the rest
-- of the session even if higher-priority headphones connect afterward. It does
-- not survive a restart, which is what this setting buys.
--
-- Must land before 90-enable-all.lua, which reads these properties when it calls
-- device_defaults.enable(); the 51- prefix is what orders it.

device_defaults.properties["use-persistent-storage"] = false
