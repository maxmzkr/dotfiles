return {
  { "ericbn/vim-solarized" },
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
