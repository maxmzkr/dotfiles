if &compatible
  set nocompatible
endif
" Add the dein installation directory into runtimepath
set runtimepath+=~/.cache/dein/repos/github.com/Shougo/dein.vim

if dein#load_state('~/.cache/dein')
  call dein#begin('~/.cache/dein')

  call dein#add('~/.cache/dein/repos/github.com/Shougo/dein.vim')
  call dein#add('nvim-lua/completion-nvim')
  call dein#add('neovim/nvim-lspconfig')
  call dein#add('vim-python/python-syntax')
  call dein#add('altercation/vim-colors-solarized')
  call dein#add('sbdchd/neoformat')
  call dein#add('nvim-lua/lsp-status.nvim')
  call dein#add('dense-analysis/ale')
  call dein#add('tpope/vim-fugitive')
  call dein#add('tpope/vim-rhubarb')

  call dein#end()
  call dein#save_state()
endif

filetype plugin indent on
syntax enable
set background=light
colorscheme solarized
let g:python_highlight_all = 1

set clipboard=unnamed
set backupdir=~/.cache/nvim/back//
set directory=~/.cache/nvim/swap//
set undodir=~/.cache/nvim/undo//

if executable('jedi-language-server')
  lua require'lspconfig'.jedi_language_server.setup{}
endif

autocmd BufEnter * lua require'completion'.on_attach()

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
nnoremap <silent> <leader>ws  <cmd>lua require'metals'.show_hover_message()<CR>
nnoremap <silent> <leader>a   <cmd>lua require'metals'.open_all_diagnostics()<CR>

let g:neoformat_enabled_python = ['isort', 'black']
augroup fmt
  autocmd!
  autocmd BufWritePre * undojoin | Neoformat
augroup END

autocmd FileType yaml setlocal ts=2 sts=2 sw=2 expandtab

set foldlevelstart=20
