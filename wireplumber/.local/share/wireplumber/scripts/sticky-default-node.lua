-- Replacement for WirePlumber's stock default-nodes/find-selected-default-node hook.
--
-- The stock hook gives the manually selected sink/source a flat +30000 priority,
-- which means a manual pick outranks every device forever. This version boosts a
-- manual pick just past whatever was already plugged in when the pick was made, so:
--
--   * the pick sticks against the devices it was chosen over
--   * a device that shows up later with a higher priority still wins
--   * if the picked device disappears, this hook stays out of the way and
--     find-best-default-node falls back to the highest priority available
--
-- Nothing here is persisted, so a fresh boot always starts on raw priority.

log = Log.open_topic ("s-default-nodes")

-- default-node.type -> { name = <node.name>, ceiling = <priority it had to beat> }
pins = {}

local function session_priority (node_props)
  local priority = node_props ["priority.session"] or node_props ["priority.driver"]
  return math.tointeger (priority) or 0
end

SimpleEventHook {
  -- Deliberately named after the stock hook: find-best-default-node declares
  -- `after = { "default-nodes/find-selected-default-node", ... }`, and reusing the
  -- name is what keeps this running before it.
  name = "default-nodes/find-selected-default-node",
  interests = {
    EventInterest {
      Constraint { "event.type", "=", "select-default-node" },
    },
  },
  execute = function (event)
    local available_nodes = event:get_data ("available-nodes")

    available_nodes = available_nodes and available_nodes:parse ()
    if not available_nodes then
      return
    end

    local props = event:get_properties ()
    local def_node_type = props ["default-node.type"]

    local source = event:get_source ()
    local metadata_om = source:call ("get-object-manager", "metadata")
    local metadata = metadata_om:lookup { Constraint { "metadata.name", "=", "default" } }
    local obj = metadata and metadata:find (0, "default.configured." .. def_node_type)

    if not obj then
      pins [def_node_type] = nil
      return
    end

    local configured = Json.Raw (obj):parse ().name
    if not configured then
      pins [def_node_type] = nil
      return
    end

    local configured_props = nil
    local highest = 0

    for _, node_props in ipairs (available_nodes) do
      local priority = session_priority (node_props)
      if priority > highest then
        highest = priority
      end
      if node_props ["node.name"] == configured then
        configured_props = node_props
      end
    end

    -- The pick is unplugged/disconnected: leave the selection to find-best.
    if not configured_props then
      return
    end

    local pin = pins [def_node_type]

    if not pin or pin.name ~= configured then
      -- A pick we haven't seen before, so this rescan is the one that followed the
      -- user making it. Everything available right now is what it was chosen over.
      pin = { name = configured, ceiling = highest }
      pins [def_node_type] = pin
      log:info ("pinning " .. configured .. " above priority " .. tostring (highest))
    end

    local priority = math.max (pin.ceiling, session_priority (configured_props)) + 1

    if priority > (event:get_data ("selected-node-priority") or 0) then
      event:set_data ("selected-node-priority", priority)
      event:set_data ("selected-node", configured)
    end
  end
}:register ()
