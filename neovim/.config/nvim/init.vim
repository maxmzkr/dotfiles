if &compatible
  set nocompatible
endif
" Add the dein installation directory into runtimepath
let g:deinpath = '~/.cache/dein/repos/github.com/Shougo/dein.vim'
exe 'set runtimepath+='.g:deinpath

if isdirectory(expand(g:deinpath))
if dein#load_state('~/.cache/dein')
  call dein#begin('~/.cache/dein')

  call dein#add('~/.cache/dein/repos/github.com/Shougo/dein.vim')
  call dein#add('nvim-lua/completion-nvim')
  call dein#add('neovim/nvim-lspconfig')
  call dein#add('vim-python/python-syntax')
  call dein#add('altercation/vim-colors-solarized')
  call dein#add('sbdchd/neoformat')
  call dein#add('nvim-lua/lsp-status.nvim')
"   call dein#add('dense-analysis/ale')
  call dein#add('tpope/vim-fugitive')
  call dein#add('tpope/vim-rhubarb')
  call dein#add('shumphrey/fugitive-gitlab.vim')
  call dein#add('junegunn/fzf', {'merged': 0})
  call dein#add('junegunn/fzf.vim', { 'depends': 'fzf' })
  call dein#add('christoomey/vim-tmux-navigator')
  call dein#add('nvim-telescope/telescope.nvim')
  call dein#add('nvim-lua/popup.nvim')
  call dein#add('nvim-lua/plenary.nvim')
  call dein#add('mbbill/undotree')

  call dein#end()
  call dein#save_state()
endif
endif

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

function HasPlugin(name)
  if !isdirectory(expand(g:deinpath))
    return 0
  endif
  return dein#check_install(["nvim-lspconfig"]) == 0
endfunction

if HasPlugin("nvim-lspconfig")
lua <<EOF
  local lsp_status = require('lsp-status')
  lsp_status.register_progress()

  lspconfig = require "lspconfig"
  lspconfig.gopls.setup {
    on_attach = lsp_status.on_attach,
    capabilities = lsp_status.capabilities,
    cmd = {"gopls", "-v", "-logfile", "auto"},
    settings = {
      gopls = {
	hoverKind = "FullDocumentation",
        staticcheck = true,
	gofumpt = true,
      },
    },
  }

  function goimports(timeoutms)
    local context = { source = { organizeImports = true, gofumpt = 1 } }
    vim.validate { context = { context, "t", true } }

    local params = vim.lsp.util.make_range_params()
    params.context = context

    local method = "textDocument/codeAction"
    local resp = vim.lsp.buf_request_sync(0, method, params, timeoutms)
    if resp and resp[1] then
      local result = resp[1].result
      if result and result[1] then
        local edit = result[1].edit
        vim.lsp.util.apply_workspace_edit(edit)
      end
    end

    -- vim.lsp.buf.formatting()
  end

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
  lspconfig.jedi_language_server.setup{
    on_attach = lsp_status.on_attach,
    capabilities = lsp_status.capabilities,
  }

  -- typescript
  require'lspconfig'.tsserver.setup{
    on_attach = lsp_status.on_attach,
    capabilities = lsp_status.capabilities,
  }

  require'lspconfig'.clangd.setup{}
EOF

autocmd BufWritePre *.go lua vim.lsp.buf.formatting_sync(nil, 10000)
autocmd BufWritePre *.go lua goimports(10000)
endif

if HasPlugin("completion")
autocmd BufEnter * lua require'completion'.on_attach()
endif

" Statusline
function! LspStatus() abort
  if luaeval('#vim.lsp.buf_get_clients() > 0')
    return luaeval("require('lsp-status').status()")
  endif

  return ''
endfunction

" Use <Tab> and <S-Tab> to navigate through popup menu
inoremap <expr> <Tab>   pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"

" Set completeopt to have a better completion experience
set completeopt=menuone,noinsert,noselect

" Avoid showing message extra message when using completion
set shortmess+=c

nnoremap <silent> gd          <cmd>lua vim.lsp.buf.definition()<CR>
nnoremap <silent> K           <cmd>lua vim.lsp.buf.hover()<CR>
nnoremap <silent> gi          <cmd>lua vim.lsp.buf.implementation()<CR>
nnoremap <silent> gr          <cmd>lua require'telescope.builtin'.lsp_references{}<CR>
nnoremap <silent> <leader>s   <cmd>lua require'telescope.builtin'.lsp_workspace_symbols{}<CR> 
nnoremap <silent> gds         <cmd>lua vim.lsp.buf.document_symbol()<CR>
nnoremap <silent> gws         <cmd>lua vim.lsp.buf.workspace_symbol()<CR>
nnoremap <silent> <leader>rn  <cmd>lua vim.lsp.buf.rename()<CR>
nnoremap <silent> <leader>f   <cmd>lua vim.lsp.buf.formatting()<CR>
nnoremap <silent> <leader>ca  <cmd>lua vim.lsp.buf.code_action()<CR>

if HasPlugin("neoformat")
let g:neoformat_enabled_python = ['black']
let g:neoformat_enabled_sql = ['pg_format']
let g:neoformat_enabled_xml = ['tidy']
let g:neoformat_enabled_go = []
augroup fmt
  autocmd!
  au BufWritePre * try | undojoin | Neoformat | catch /^Vim\%((\a\+)\)\=:E790/ | finally | silent Neoformat | endtry
augroup END
endif

autocmd FileType yaml setlocal ts=2 sts=2 sw=2 expandtab
autocmd FileType typescript setlocal ts=2 sts=2 sw=2 expandtab
autocmd FileType json setlocal ts=2 sts=2 sw=2 expandtab

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

if HasPlugin("ale")
	let g:ale_linters = {
	\	'go': [],
	\}
endif
