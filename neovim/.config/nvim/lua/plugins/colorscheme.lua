return {
  { "maxmx03/solarized.nvim" },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "solarized",
    },
    init = function()
      vim.go.background = "light"
    end,
  },
}
