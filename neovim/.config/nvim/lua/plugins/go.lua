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
      -- add golangci-lint
      table.insert(
        opts.sources,
        nls.builtins.diagnostics.golangci_lint.with({
          extra_args = function(params)
            -- disable govet because gopls has "all the usual bug-finding analyzers from the go vet suite"
            -- disable staticcheck because "In addition, gopls includes the staticcheck suite"
            -- https://github.com/golang/tools/blob/master/gopls/doc/analyzers.md
            -- run golangci-lint only on the current package because it's slow on the full project
            return { "-D", "govet", "-D", "staticcheck", vim.fs.dirname(params.bufname) }
          end,
        })
      )
      opts.debug = true
    end,
  },
}
