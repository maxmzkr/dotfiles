return {
  -- disable gofumpt
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        gopls = {
          settings = {
            gopls = {
              gofumpt = false,
            },
          },
        },
      },
    },
  },
  {
    "nvimtools/none-ls.nvim",
    opts = function(_, opts)
      local nls = require("null-ls")
      opts.sources = vim.tbl_filter(function(source)
        return source.name ~= nls.builtins.formatting.gofumpt.name
      end, opts.sources or {})
    end,
  },
}
