return {
  {
    "zbirenbaum/copilot-cmp",
    enabled = false,
  },
  {
    "zbirenbaum/copilot.lua",
    event = "InsertEnter",
    opts = {
      suggestion = {
        enabled = true,
        auto_trigger = true,
      },
      panel = { enabled = true },
    },
  },
  -- it seems like adding noselect prevents the cmp completion ghost text from conflicting with the copilot completion
  {
    "hrsh7th/nvim-cmp",
    opts = {
      completion = {
        completeopt = "menu,menuone,noinsert,noselect",
      },
    },
  },
}
