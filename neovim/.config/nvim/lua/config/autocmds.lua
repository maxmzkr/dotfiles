-- Autocmds are automatically loaded on the VeryLazy event
-- Default autocmds that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
-- Add any additional autocmds here

local function augroup(name)
	return vim.api.nvim_create_augroup("maxmzkr_" .. name, { clear = true })
end

-- wrap and check for spell in go filetypes
vim.api.nvim_create_autocmd("FileType", {
	group = augroup("wrap_go_spell"),
	pattern = { "go", "gomod", "gomodinfo", "gomodgraph", "gomodwhy" },
	callback = function()
		vim.opt_local.wrap = true
		vim.opt_local.spell = true

		-- add camel to spell options
		vim.opt_local.spelloptions:append("camel")
	end,
})

-- wrap and check for spell in go filetypes
vim.api.nvim_create_autocmd("FileType", {
	group = augroup("proto_spell"),
	pattern = { "proto" },
	callback = function()
		vim.opt_local.wrap = true
		vim.opt_local.spell = true

		-- add camel to spell options
		vim.opt_local.spelloptions:append("camel")
	end,
})
