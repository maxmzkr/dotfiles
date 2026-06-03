return {
	{
		"ravitemer/mcphub.nvim",
		dependencies = { "nvim-lua/plenary.nvim" },
		build = "bundled_build.lua",
		lazy = false,
		cmd = "MCPHub",
		keys = {
			{ "<leader>am", "<cmd>MCPHub<cr>", desc = "MCP Hub" },
		},
		opts = {
			use_bundled_binary = true,
			auto_approve = false,
			workspace = {
				look_for = { ".mcphub/servers.json" },
			},
			extensions = {
				codecompanion = {
					show_result_in_chat = true,
					make_vars = true,
					make_slash_commands = true,
				},
			},
		},
	},
}
