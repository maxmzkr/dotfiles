require("plugins")

vim.cmd("set termguicolors")

vim.cmd("set number")

vim.cmd([[
  augroup packer_user_config
    autocmd!
    autocmd BufWritePost plugins.lua source <afile> | PackerCompile
  augroup end
]])

-- Setup treesitter
require("nvim-treesitter.configs").setup({
  -- A list of parser names, or "all"
  ensure_installed = { "go" },

  -- Install parsers synchronously (only applied to `ensure_installed`)
  sync_install = false,

  -- List of parsers to ignore installing (for "all")
  -- ignore_install = { "javascript" },

  highlight = {
    -- `false` will disable the whole extension
    enable = true,

    -- NOTE: these are the names of the parsers and not the filetype. (for example if you want to
    -- disable highlighting for the `tex` filetype, you need to include `latex` in this list as this is
    -- the name of the parser)
    -- list of language that will be disabled
    -- disable = { "c", "rust" },

    -- Setting this to true will run `:h syntax` and tree-sitter at the same time.
    -- Set this to `true` if you depend on 'syntax' being enabled (like for indentation).
    -- Using this option may slow down your editor, and you may see some duplicate highlights.
    -- Instead of true it can also be a list of languages
    additional_vim_regex_highlighting = false,
  },
})

-- lspkind
local lspkind = require("lspkind")
lspkind.init({
  symbol_map = {
    Copilot = "",
  },
})

-- Setup nvim-cmp.
local cmp = require("cmp")
local types = require("cmp.types")

cmp.setup({
  preselect = cmp.PreselectMode.Item,
  mapping = {
    ["<C-b>"] = cmp.mapping(cmp.mapping.scroll_docs(-4), { "i", "c" }),
    ["<C-f>"] = cmp.mapping(cmp.mapping.scroll_docs(4), { "i", "c" }),
    ["<C-Space>"] = cmp.mapping(cmp.mapping.complete(), { "i", "c" }),
    ["<C-y>"] = cmp.config.disable, -- Specify `cmp.config.disable` if you want to remove the default `<C-y>` mapping.
    ["<C-e>"] = cmp.mapping({
      i = cmp.mapping.abort(),
      c = cmp.mapping.close(),
    }),
    ["<C-n>"] = cmp.mapping(cmp.mapping.select_next_item({ behavior = types.cmp.SelectBehavior.Insert }), {
      "i",
      "c",
    }),
    ["<C-p>"] = cmp.mapping(cmp.mapping.select_prev_item({ behavior = types.cmp.SelectBehavior.Insert }), {
      "i",
      "c",
    }),
    ["<CR>"] = cmp.mapping.confirm({
      -- this is the important line
      behavior = cmp.ConfirmBehavior.Replace,
      select = true,
    }),
  },
  snippet = {
    -- REQUIRED - you must specify a snippet engine
    expand = function(args)
      vim.fn["vsnip#anonymous"](args.body) -- For `vsnip` users.
      -- require('luasnip').lsp_expand(args.body) -- For `luasnip` users.
      -- require('snippy').expand_snippet(args.body) -- For `snippy` users.
      -- vim.fn["UltiSnips#Anon"](args.body) -- For `ultisnips` users.
    end,
  },
  window = {
    -- completion = cmp.config.window.bordered(),
    -- documentation = cmp.config.window.bordered(),
  },
  sources = cmp.config.sources({
    { name = "nvim_lsp" },
    { name = "vsnip" }, -- For vsnip users.
    { name = "nvim_lsp_signature_help" },
    { name = "emoji" },
    { name = "copilot" },
    -- { name = 'luasnip' }, -- For luasnip users.
    -- { name = 'ultisnips' }, -- For ultisnips users.
    -- { name = 'snippy' }, -- For snippy users.
  }, {
    { name = "buffer" },
  }),
  sorting = {
    comparators = {
      cmp.config.compare.recently_used,
      cmp.config.compare.exact,
      cmp.config.compare.score,
      cmp.config.compare.length,
      cmp.config.compare.sort_text,
      cmp.config.compare.kind,
      cmp.config.compare.order,
      cmp.config.compare.offset,
    },
  },
  experimental = {
    ghost_text = true,
  },
  formatting = {
    format = function(entry, vim_item)
      if vim.tbl_contains({ "path" }, entry.source.name) then
        local icon, hl_group = require("nvim-web-devicons").get_icon(entry:get_completion_item().label)
        if icon then
          vim_item.kind = icon
          vim_item.kind_hl_group = hl_group
          return vim_item
        end
      end
      return require("lspkind").cmp_format({ with_text = false })(entry, vim_item)
    end,
  },
})

-- Use buffer source for `/` (if you enabled `native_menu`, this won't work anymore).
cmp.setup.cmdline("/", {
  sources = {
    { name = "buffer" },
  },
})

-- Use cmdline & path source for ':' (if you enabled `native_menu`, this won't work anymore).
cmp.setup.cmdline(":", {
  sources = cmp.config.sources({
    { name = "path" },
  }, {
    { name = "cmdline" },
  }),
})

-- Setup lspconfig.
local capabilities = require("cmp_nvim_lsp").default_capabilities(vim.lsp.protocol.make_client_capabilities())
local lsp_status = require("lsp-status")
lsp_status.register_progress()

lspconfig = require("lspconfig")

function organizeImports(client, timeoutms)
  local context = { source = { organizeImports = true, gofumpt = 1 } }
  vim.validate({ context = { context, "t", true } })

  local params = vim.lsp.util.make_range_params()
  params.context = context

  local method = "textDocument/codeAction"
  local resp = vim.lsp.buf_request_sync(0, method, params, timeoutms)
  if resp and resp[1] then
    local result = resp[1].result
    if result and result[1] then
      local edit = result[1].edit
      vim.lsp.util.apply_workspace_edit(edit, client.offset_encoding)
    end
  end
end

local dap = require("dap")
require("dap-go").setup()

lspconfig.gopls.setup({
  on_attach = function(client, bufnr)
    vim.api.nvim_create_autocmd({ "BufWritePre" }, {
      pattern = { "<buffer>" },
      callback = function()
        organizeImports(client, 1000)
        vim.lsp.buf.format(nil, 100000)
      end,
    })
    lsp_status.on_attach(client, bufnr)
  end,
  capabilities = lsp_status.capabilities,
  cmd = { "gopls", "-vv", "-rpc.trace", "-logfile", "auto" },
  settings = {
    gopls = {
      hoverKind = "FullDocumentation",
      staticcheck = true,
      gofumpt = true,
      ["local"] = "github.com/censys",
    },
  },
})

do
  local method = "textDocument/publishDiagnostics"
  local default_callback = vim.lsp.handlers[method]
  vim.lsp.handlers[method] = function(err, method, result, client_id)
    default_callback(err, method, result, client_id)
    if result and result.diagnostics then
      for _, v in ipairs(result.diagnostics) do
        v.bufnr = client_id
        v.lnum = v.range.start.line + 1
        v.col = v.range.start.character + 1
        v.text = v.message
      end
      vim.lsp.util.set_qflist(result.diagnostics)
    end
  end
end

-- python
lspconfig.jedi_language_server.setup({
  on_attach = lsp_status.on_attach,
  capabilities = lsp_status.capabilities,
})

-- typescript
require("lspconfig").tsserver.setup({
  on_attach = lsp_status.on_attach,
  capabilities = lsp_status.capabilities,
})

require("lspconfig").clangd.setup({})

vim.opt_global.shortmess:remove("F")

vim.opt_global.shortmess:append("c")

local metals_config = require("metals").bare_config()

-- Example of settings
metals_config.settings = {
  showImplicitArguments = true,
  showImplicitConversionsAndClasses = true,
  showInferredType = true,
  excludedPackages = { "akka.actor.typed.javadsl", "com.github.swagger.akka.javadsl" },
  serverProperties = { "-Xmx4g" },
}
local function map(mode, lhs, rhs, opts)
  local options = { noremap = true }
  if opts then
    options = vim.tbl_extend("force", options, opts)
  end
  vim.api.nvim_set_keymap(mode, lhs, rhs, options)
end

-- LSP mappings
vim.keymap.set("n", "gD", require("telescope.builtin").lsp_definitions, {})
vim.keymap.set("n", "gt", require("telescope.builtin").lsp_type_definitions, {})
vim.keymap.set("n", "K", vim.lsp.buf.hover, {})
vim.keymap.set("n", "gi", require("telescope.builtin").lsp_implementations, {})
vim.keymap.set("n", "gr", require("telescope.builtin").lsp_references, {})
vim.keymap.set("n", "gds", require("telescope.builtin").lsp_document_symbols, {})
vim.keymap.set("n", "gws", require("telescope.builtin").lsp_workspace_symbols, {})
vim.keymap.set("n", "<leader>cl", vim.lsp.codelens.run, {})
vim.keymap.set("n", "<leader>sh", vim.lsp.buf.signature_help, {})
vim.keymap.set("n", "<leader>rn", vim.lsp.buf.rename, {})
vim.keymap.set("n", "<leader>f", function()
  vim.lsp.buf.format({ async = true })
end, {})
vim.keymap.set("n", "<leader>ca", function()
  vim.lsp.buf.code_action()
end, {})
vim.keymap.set("n", "<leader>ws", require("metals").hover_worksheet, {})
vim.keymap.set("n", "<leader>aa", vim.diagnostic.setqflist, {}) -- all workspace diagnostics
vim.keymap.set("n", "<leader>ae", function()
  vim.diagnostic.setqflist({ severity = "E" })
end, {}) -- all workspace errors
vim.keymap.set("n", "<leader>aw", function()
  vim.diagnostic.setqflist({ severity = "W" })
end, {}) -- all workspace warnings
vim.keymap.set("n", "<leader>d", function()
  vim.diagnostic.setloclist()
end, {}) -- buffer diagnostics only
vim.keymap.set("n", "[c", function()
  vim.diagnostic.goto_prev({ wrap = false })
end, {})
vim.keymap.set("n", "]c", function()
  vim.diagnostic.goto_next({ wrap = false })
end, {})
vim.keymap.set("n", "<leader>sd", function()
  vim.diagnostic.open_float(0, { scope = "line" })
end, {})

-- Example mappings for usage with nvim-dap. If you don't use that, you can
-- skip these
map("n", "<leader>dc", [[<cmd>lua require"dap".continue()<CR>]])
map("n", "<leader>dr", [[<cmd>lua require"dap".repl.toggle()<CR>]])
map("n", "<leader>dK", [[<cmd>lua require"dap.ui.widgets".hover()<CR>]])
map("n", "<leader>dt", [[<cmd>lua require"dap".toggle_breakpoint()<CR>]])
map("n", "<leader>dso", [[<cmd>lua require"dap".step_over()<CR>]])
map("n", "<leader>dsi", [[<cmd>lua require"dap".step_into()<CR>]])
map("n", "<leader>dl", [[<cmd>lua require"dap".run_last()<CR>]])

-- *READ THIS*
-- I *highly* recommend setting statusBarProvider to true, however if you do,
-- you *have* to have a setting to display this in your statusline or else
-- you'll not see any messages from metals. There is more info in the help
-- docs about this
metals_config.init_options.statusBarProvider = "on"

-- Example if you are using cmp how to make sure the correct capabilities for snippets are set
metals_config.capabilities = capabilities

-- Debug settings if you're using nvim-dap
dap.configurations.scala = {
  {
    type = "scala",
    request = "launch",
    name = "RunOrTest",
    metals = {
      runType = "runOrTestFile",
      --args = { "firstArg", "secondArg", "thirdArg" }, -- here just as an example
    },
  },
  {
    type = "scala",
    request = "launch",
    name = "Test Target",
    metals = {
      runType = "testTarget",
    },
  },
}

metals_config.on_attach = function(client, bufnr)
  require("metals").setup_dap()
  vim.api.nvim_create_autocmd({ "BufWritePre" }, {
    pattern = { "<buffer>" },
    callback = function()
      vim.lsp.buf.format(nil, 5000)
    end,
  })
  vim.api.nvim_create_autocmd({ "BufWritePost" }, {
    pattern = { "<buffer>" },
    callback = function()
      -- res, err = vim.lsp.buf_request_sync(
      --   0,
      --   "workspace/executeCommand",
      --   { command = "metals.scalafix-run", arguments = { vim.lsp.util.make_position_params() } },
      --   5000
      -- )
      -- if err ~= nil then
      --   vim.notify("Error running scalafix: " .. err)
      -- end

      if vim.fn.getbufinfo(vim.fn.buffer_number())[1].changed == 1 then
        vim.cmd("write")
      end
    end,
  })
  on_attach(client, bufnr)
end

-- Autocmd that will actually be in charging of starting the whole thing
local nvim_metals_group = vim.api.nvim_create_augroup("nvim-metals", { clear = true })
vim.api.nvim_create_autocmd("FileType", {
  -- NOTE: You may or may not want java included here. You will need it if you
  -- want basic Java support but it may also conflict if you are using
  -- something like nvim-jdtls which also works on a java filetype autocmd.
  pattern = { "scala", "sbt" },
  callback = function()
    require("metals").initialize_or_attach(metals_config)
  end,
  group = nvim_metals_group,
})

require("lspconfig").ccls.setup({})

local actions = require("telescope.actions")
local trouble = require("trouble.providers.telescope")

local telescope = require("telescope")

telescope.setup({
  defaults = {
    mappings = {
      i = { ["<c-t>"] = trouble.open_with_trouble },
      n = { ["<c-t>"] = trouble.open_with_trouble },
    },
  },
})

require("gitsigns").setup({
  signs = {
    add = { hl = "GitGutterAdd", text = "▋" },
    change = { hl = "GitGutterChange", text = "▋" },
    delete = { hl = "GitGutterDelete", text = "▋" },
    topdelete = { hl = "GitGutterDeleteChange", text = "▔" },
    changedelete = { hl = "GitGutterChange", text = "▎" },
  },
  keymaps = {
    -- Default keymap options
    noremap = true,
    buffer = true,

    ["n ]g"] = { expr = true, "&diff ? ']g' : '<cmd>lua require\"gitsigns\".next_hunk()<CR>'" },
    ["n [g"] = { expr = true, "&diff ? '[g' : '<cmd>lua require\"gitsigns\".prev_hunk()<CR>'" },

    ["n <leader>hs"] = '<cmd>lua require"gitsigns".stage_hunk()<CR>',
    ["n <leader>hu"] = '<cmd>lua require"gitsigns".undo_stage_hunk()<CR>',
    ["n <leader>hr"] = '<cmd>lua require"gitsigns".reset_hunk()<CR>',
    ["n <leader>hp"] = '<cmd>lua require"gitsigns".preview_hunk()<CR>',
    ["n <leader>hb"] = '<cmd>lua require"gitsigns".blame_line()<CR>',

    -- Text objects
    ["o ih"] = ':<C-U>lua require"gitsigns".text_object()<CR>',
    ["x ih"] = ':<C-U>lua require"gitsigns".text_object()<CR>',
  },
})

local gl = require("galaxyline")
local colors = require("galaxyline.theme").default

local colors = {
  bg = "#073642",
  line_bg = "#073642",
  yellow = "#b58900",
  cyan = "#2aa198",
  darkblue = "#081633",
  green = "#859900",
  orange = "#cb4b16",
  purple = "#5d4d7a",
  magenta = "#d33682",
  grey = "#c0c0c0",
  blue = "#268bd2",
  red = "#dc322f",
}

local condition = require("galaxyline.condition")
local gls = gl.section
gl.short_line_list = { "NvimTree", "vista", "dbui", "packer" }

gls.left[1] = {
  RainbowRed = {
    provider = function()
      return "▊ "
    end,
    highlight = { colors.blue, colors.bg },
  },
}
gls.left[2] = {
  ViMode = {
    provider = function()
      -- auto change color according the vim mode
      local mode_color = {
        n = colors.red,
        i = colors.green,
        v = colors.blue,
        [""] = colors.blue,
        V = colors.blue,
        c = colors.magenta,
        no = colors.red,
        s = colors.orange,
        S = colors.orange,
        [""] = colors.orange,
        ic = colors.yellow,
        R = colors.violet,
        Rv = colors.violet,
        cv = colors.red,
        ce = colors.red,
        r = colors.cyan,
        R = colors.cyan,
        rm = colors.cyan,
        ["r?"] = colors.cyan,
        ["!"] = colors.red,
        t = colors.red,
      }
      vim.api.nvim_command("hi GalaxyViMode guifg=" .. mode_color[vim.fn.mode()] .. " guibg=" .. colors.bg)
      return "  "
    end,
  },
}
gls.left[3] = {
  FileSize = {
    provider = "FileSize",
    condition = condition.buffer_not_empty,
    highlight = { colors.fg, colors.bg },
  },
}
gls.left[4] = {
  FileIcon = {
    provider = "FileIcon",
    condition = condition.buffer_not_empty,
    highlight = { require("galaxyline.provider_fileinfo").get_file_icon_color, colors.bg },
  },
}

gls.left[5] = {
  FileName = {
    provider = "FileName",
    condition = condition.buffer_not_empty,
    highlight = { colors.fg, colors.bg, "bold" },
  },
}

gls.left[6] = {
  LineInfo = {
    provider = function()
      local line = vim.fn.line(".")
      local col = vim.fn.col(".")
      local virtcol = vim.fn.virtcol(".")
      if col ~= virtcol then
        return string.format("%3d :%2d-%2d ", line, col, virtcol)
      end
      return string.format("%3d :%2d ", line, col)
    end,
    separator = " ",
    separator_highlight = { "NONE", colors.bg },
    highlight = { colors.fg, colors.bg },
  },
}

gls.left[7] = {
  PerCent = {
    provider = "LinePercent",
    separator = " ",
    separator_highlight = { "NONE", colors.bg },
    highlight = { colors.fg, colors.bg, "bold" },
  },
}

gls.left[8] = {
  DiagnosticError = {
    provider = "DiagnosticError",
    icon = "  ",
    highlight = { colors.red, colors.bg },
  },
}
gls.left[9] = {
  DiagnosticWarn = {
    provider = "DiagnosticWarn",
    icon = "  ",
    highlight = { colors.yellow, colors.bg },
  },
}

gls.left[10] = {
  DiagnosticHint = {
    provider = "DiagnosticHint",
    icon = "  ",
    highlight = { colors.cyan, colors.bg },
  },
}

gls.left[11] = {
  DiagnosticInfo = {
    provider = "DiagnosticInfo",
    icon = "  ",
    highlight = { colors.blue, colors.bg },
  },
}

gls.mid[1] = {
  ShowLspClient = {
    provider = "GetLspClient",
    condition = function()
      local tbl = { ["dashboard"] = true, [""] = true }
      if tbl[vim.bo.filetype] then
        return false
      end
      return true
    end,
    icon = " LSP:",
    highlight = { colors.yellow, colors.bg, "bold" },
  },
}

gls.mid[2] = {
  MetalsStatus = {
    provider = function()
      return "  " .. (vim.g["metals_status"] or "")
    end,
    condition = function()
      return require("galaxyline.provider_lsp").get_lsp_client() == "metals"
    end,
    highlight = { colors.yellow, colors.bg, "bold" },
  },
}

gls.right[1] = {
  FileEncode = {
    provider = "FileEncode",
    condition = condition.hide_in_width,
    separator = " ",
    separator_highlight = { "NONE", colors.bg },
    highlight = { colors.green, colors.bg, "bold" },
  },
}

gls.right[2] = {
  FileFormat = {
    provider = "FileFormat",
    condition = condition.hide_in_width,
    separator = " ",
    separator_highlight = { "NONE", colors.bg },
    highlight = { colors.green, colors.bg, "bold" },
  },
}

gls.right[3] = {
  GitIcon = {
    provider = function()
      return "  "
    end,
    condition = condition.check_git_workspace,
    separator = " ",
    separator_highlight = { "NONE", colors.bg },
    highlight = { colors.violet, colors.bg, "bold" },
  },
}

gls.right[4] = {
  GitBranch = {
    provider = "GitBranch",
    condition = condition.check_git_workspace,
    highlight = { colors.violet, colors.bg, "bold" },
  },
}

gls.right[5] = {
  DiffAdd = {
    provider = "DiffAdd",
    condition = condition.hide_in_width,
    icon = "  ",
    highlight = { colors.green, colors.bg },
  },
}
gls.right[6] = {
  DiffModified = {
    provider = "DiffModified",
    condition = condition.hide_in_width,
    icon = " 柳",
    highlight = { colors.orange, colors.bg },
  },
}
gls.right[7] = {
  DiffRemove = {
    provider = "DiffRemove",
    condition = condition.hide_in_width,
    icon = "  ",
    highlight = { colors.red, colors.bg },
  },
}

gls.right[8] = {
  RainbowBlue = {
    provider = function()
      return " ▊"
    end,
    highlight = { colors.blue, colors.bg },
  },
}

gls.short_line_left[1] = {
  BufferType = {
    provider = "FileTypeName",
    separator = " ",
    separator_highlight = { "NONE", colors.bg },
    highlight = { colors.blue, colors.bg, "bold" },
  },
}

gls.short_line_left[2] = {
  SFileName = {
    provider = "SFileName",
    condition = condition.buffer_not_empty,
    highlight = { colors.fg, colors.bg, "bold" },
  },
}

gls.short_line_right[1] = {
  BufferIcon = {
    provider = "BufferIcon",
    highlight = { colors.fg, colors.bg },
  },
}

vim.g["indentLine_char_list"] = { "" }
vim.g["vim_json_conceal"] = 0
vim.g["markdown_syntax_conceal"] = 0

vim.api.nvim_exec(
  [[
filetype plugin indent on
syntax enable
set background=light
silent! colorscheme solarized
let g:python_highlight_all = 1

set clipboard=unnamedplus
let backupdir = '~/.cache/nvim/back//'
if isdirectory(expand(backupdir))
  exe 'set backupdir='.backupdir
endif
set directory=~/.cache/nvim/swap//
set undofile
set undodir=~/.cache/nvim/undo//

if executable('jedi-language-server')
  lua require'lspconfig'.jedi_language_server.setup{}
endif

" Statusline
function! LspStatus() abort
  if luaeval('#vim.lsp.buf_get_clients() > 0')
    return luaeval("require('lsp-status').status()")
  endif

  return ''
endfunction


" Set completeopt to have a better completion experience
set completeopt=menuone,noinsert,noselect

" Avoid showing message extra message when using completion
set shortmess+=c

let g:neoformat_enabled_python = ['black']
let g:neoformat_enabled_sql = ['pg_format']
let g:neoformat_enabled_xml = ['tidy']
let g:neoformat_enabled_go = []
let g:neoformat_enabled_scala = []
let g:neoformat_enabled_sbt = []
let g:neoformat_enabled_sql = ['sqlformat']
augroup fmt
  autocmd!
  au BufWritePre * try | undojoin | Neoformat | catch /^Vim\%((\a\+)\)\=:E790/ | finally | silent Neoformat | endtry
augroup END

autocmd FileType yaml setlocal ts=2 sts=2 sw=2 expandtab
autocmd FileType typescript setlocal ts=2 sts=2 sw=2 expandtab
autocmd FileType json setlocal ts=2 sts=2 sw=2 expandtab
autocmd FileType proto setlocal ts=2 sts=2 sw=2 expandtab
autocmd FileType lua setlocal ts=2 sts=2 sw=2 expandtab
autocmd FileType tpl setlocal ts=2 sts=2 sw=2 expandtab
au BufRead,BufNewFile *.sls set filetype=yaml

autocmd FileType proto nnoremap <silent> <buffer> <leader>pb  <cmd>e %:p:r.pb.go<CR>
autocmd FileType go nnoremap <silent> <buffer> <leader>pb  <cmd>e %:p:r:r.proto<CR>

set foldlevelstart=20

function! RipgrepFzf(query, fullscreen)
  let command_fmt = 'rg --hidden --column --line-number --no-heading --color=always --smart-case -- %s || true'
  let initial_command = printf(command_fmt, shellescape(a:query))
  let reload_command = printf(command_fmt, '{q}')
  let spec = {'options': ['--phony', '--query', a:query, '--bind', 'change:reload:'.reload_command]}
  call fzf#vim#grep(initial_command, 1, fzf#vim#with_preview(spec), a:fullscreen)
endfunction

command! -nargs=* -bang RG call RipgrepFzf(<q-args>, <bang>0)

command! -bang -nargs=? -complete=dir Files
    \ call fzf#vim#files(<q-args>, fzf#vim#with_preview({'options': ['--layout=reverse', '--info=inline']}), <bang>0)

" An action can be a reference to a function that processes selected lines
function! s:build_quickfix_list(lines)
  call setqflist(map(copy(a:lines), '{ "filename": v:val }'))
  copen
  cc
endfunction

let g:fzf_action = {
  \ 'ctrl-q': function('s:build_quickfix_list'),
  \ 'ctrl-t': 'tab split',
  \ 'ctrl-x': 'split',
  \ 'ctrl-v': 'vsplit' }

" - Window using a Vim command
let g:fzf_layout = { 'tmux': '-d30%' }

" Customize fzf colors to match your color scheme
" - fzf#wrap translates this to a set of `--color` options
let g:fzf_colors =
\ { 'fg':      ['fg', 'Normal'],
  \ 'bg':      ['bg', 'Normal'],
  \ 'hl':      ['fg', 'Comment'],
  \ 'fg+':     ['fg', 'CursorLine', 'CursorColumn', 'Normal'],
  \ 'bg+':     ['bg', 'CursorLine', 'CursorColumn'],
  \ 'hl+':     ['fg', 'Statement'],
  \ 'info':    ['fg', 'PreProc'],
  \ 'border':  ['fg', 'Ignore'],
  \ 'prompt':  ['fg', 'Conditional'],
  \ 'pointer': ['fg', 'Exception'],
  \ 'marker':  ['fg', 'Keyword'],
  \ 'spinner': ['fg', 'Label'],
  \ 'header':  ['fg', 'Comment'] }

" Enable per-command history
" - History files will be stored in the specified directory
" - When set, CTRL-N and CTRL-P will be bound to 'next-history' and
"   'previous-history' instead of 'down' and 'up'.
let g:fzf_history_dir = '~/.local/share/fzf-history'

" Set up key bindings for fzf
nnoremap <C-p> :FZF<Cr>
nnoremap <C-g> :RG<Cr>

" Reopen files at the same location as was left off
autocmd BufReadPost *
\ if line("'\"") >= 1 && line("'\"") <= line("$") && &ft !~# 'commit'
\ |   exe "normal! g`\""
\ | endif

set spell

" NOTE: You can use other key to expand snippet.

" Expand
imap <expr> <C-j>   vsnip#expandable()  ? '<Plug>(vsnip-expand)'         : '<C-j>'
smap <expr> <C-j>   vsnip#expandable()  ? '<Plug>(vsnip-expand)'         : '<C-j>'

" Expand or jump
imap <expr> <C-l>   vsnip#available(1)  ? '<Plug>(vsnip-expand-or-jump)' : '<C-l>'
smap <expr> <C-l>   vsnip#available(1)  ? '<Plug>(vsnip-expand-or-jump)' : '<C-l>'

" Jump forward or backward
imap <expr> <Tab>   vsnip#jumpable(1)   ? '<Plug>(vsnip-jump-next)'      : '<Tab>'
smap <expr> <Tab>   vsnip#jumpable(1)   ? '<Plug>(vsnip-jump-next)'      : '<Tab>'
imap <expr> <S-Tab> vsnip#jumpable(-1)  ? '<Plug>(vsnip-jump-prev)'      : '<S-Tab>'
smap <expr> <S-Tab> vsnip#jumpable(-1)  ? '<Plug>(vsnip-jump-prev)'      : '<S-Tab>'

" Select or cut text to use as $TM_SELECTED_TEXT in the next snippet.
" See https://github.com/hrsh7th/vim-vsnip/pull/50
nmap        s   <Plug>(vsnip-select-text)
xmap        s   <Plug>(vsnip-select-text)
nmap        S   <Plug>(vsnip-cut-text)
xmap        S   <Plug>(vsnip-cut-text)

" If you want to use snippet for multiple filetypes, you can `g:vsnip_filetypes` for it.
let g:vsnip_filetypes = {}
let g:vsnip_filetypes.javascriptreact = ['javascript']
let g:vsnip_filetypes.typescriptreact = ['typescript']

set conceallevel=0
let g:vim_json_syntax_conceal = 0

]],
  true
)
