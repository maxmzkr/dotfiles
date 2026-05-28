return {
	-- didn't work
	--	{
	--		"nvim-treesitter/playground",
	--		config = function()
	--			require("nvim-treesitter.configs").setup({
	--				playground = {
	--					enable = true,
	--					updatetime = 25, -- Debounced time for highlighting nodes in the playground
	--					persist_queries = false, -- Whether the query persists across vim sessions
	--				},
	--			})
	--		end,
	--	},
	{
		"nvim-treesitter/nvim-treesitter",
		opts = function(_, opts)
			local parser_config = require("nvim-treesitter.parsers")
			parser_config.cenql = {
				install_info = {
					url = "~/tree-sitter-cenql",
					files = { "src/parser.c" },
					branch = "main",
					generate_requires_npm = false,
					requires_generate_from_grammar = false,
				},
				filetype = "cenql",
			}
			vim.filetype.add({ extension = { cenql = "cenql" } })
		end,
	},
	{
		"nvim-treesitter/nvim-treesitter",
		opts = {
			ensure_installed = { "cenql", "proto" },
		},
	},
}
