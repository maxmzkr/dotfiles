local function override_diff_highlights()
  -- Solarized light palette, subtle backgrounds for diff highlighting.
  -- Stock solarized.nvim / many colorschemes pick over-saturated greens and
  -- reds that turn an all-added file into an unreadable wall of color.
  local sets = {
    DiffAdd = { bg = "#e6efc2", fg = "NONE" },
    DiffChange = { bg = "#ece7d0", fg = "NONE" },
    DiffText = { bg = "#cfe2b8", fg = "NONE", bold = true },
    DiffDelete = { bg = "#f4d4d0", fg = "#dc322f" },
    -- gitsigns signs/lines pick these up too
    GitSignsAddLn = { bg = "#e6efc2" },
    GitSignsChangeLn = { bg = "#ece7d0" },
    GitSignsDeleteLn = { bg = "#f4d4d0" },
    -- diffview file panel additions
    DiffviewDiffAddAsDelete = { bg = "#f4d4d0" },
    DiffviewDiffDelete = { fg = "#93a1a1", bg = "NONE" },
    -- octo review panes link DiffText to these per-window; upstream defaults are
    -- GitHub's dark green/red, dark enough to need white fg. Stay at the same
    -- lightness as the line backgrounds above and get the emphasis from
    -- saturation instead, so syntax colors stay readable on top.
    OctoReviewDiffAddText = { bg = "#d9eeae", fg = "NONE", bold = true },
    OctoReviewDiffDeleteText = { bg = "#ffd0c2", fg = "NONE", bold = true },
  }
  for group, val in pairs(sets) do
    vim.api.nvim_set_hl(0, group, val)
  end
end

return {
  { "maxmx03/solarized.nvim" },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "solarized",
    },
    init = function()
      vim.go.background = "light"
      vim.api.nvim_create_autocmd("ColorScheme", {
        pattern = "*",
        callback = override_diff_highlights,
      })
    end,
  },
}
