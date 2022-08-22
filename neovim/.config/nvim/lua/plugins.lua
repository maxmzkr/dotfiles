-- This file can be loaded by calling `lua require('plugins')` from your init.vim

local fn = vim.fn
local install_path = fn.stdpath('data')..'/site/pack/packer/start/packer.nvim'
if fn.empty(fn.glob(install_path)) > 0 then
  packer_bootstrap = fn.system({'git', 'clone', '--depth', '1', 'https://github.com/wbthomason/packer.nvim', install_path})
end

return require('packer').startup(function(use)
  -- My plugins here
  -- use 'foo1/bar1.nvim'
  -- use 'foo2/bar2.nvim'
  use 'hrsh7th/cmp-nvim-lsp'
  use 'hrsh7th/cmp-buffer'
  use 'hrsh7th/cmp-path'
  use 'hrsh7th/cmp-cmdline'
  use 'hrsh7th/nvim-cmp'
  use 'hrsh7th/cmp-vsnip'
  use 'hrsh7th/vim-vsnip'
  use 'hrsh7th/vim-vsnip-integ'
  use 'golang/vscode-go'
  use 'neovim/nvim-lspconfig'
  use 'vim-python/python-syntax'
  use 'ericbn/vim-solarized'
  use 'sbdchd/neoformat'
  use 'nvim-lua/lsp-status.nvim'
  use 'tpope/vim-fugitive'
  use 'tpope/vim-rhubarb'
  use 'shumphrey/fugitive-gitlab.vim'
  use {
    'junegunn/fzf.vim',
    requires = {{'junegunn/fzf'}}
  }
  use 'christoomey/vim-tmux-navigator'
  use 'nvim-telescope/telescope.nvim'
  use 'nvim-lua/popup.nvim'
  use 'nvim-lua/plenary.nvim'
  use {
    'mbbill/undotree',
    run = ':TSUpdate'
  }
  use 'PeterRincker/vim-argumentative'
  use 'mfussenegger/nvim-jdtls'
  use 'hashivim/vim-terraform'
  use 'folke/trouble.nvim'
  use 'kyazdani42/nvim-web-devicons'
  use 'scalameta/nvim-metals'
  use 'mfussenegger/nvim-dap'
  use 'leoluz/nvim-dap-go'
  use 'nvim-treesitter/nvim-treesitter'
  use {
    'glepnir/galaxyline.nvim',
    requires = 'kyazdani42/nvim-web-devicons'
  }
  use 'lewis6991/gitsigns.nvim'
  use {
    "SmiteshP/nvim-gps",
    requires = "nvim-treesitter/nvim-treesitter"
  }

  use 'Yggdroot/indentLine'
  use 'github/copilot.vim'


  -- Automatically set up your configuration after cloning packer.nvim
  -- Put this at the end after all plugins
  if packer_bootstrap then
    require('packer').sync()
  end
end)
