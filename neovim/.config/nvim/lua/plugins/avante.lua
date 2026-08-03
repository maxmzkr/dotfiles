return {
	{
		"yetone/avante.nvim",
		enabled = false,
		version = false,
		dependencies = {
			"nvim-lua/plenary.nvim",
			"nvim-treesitter/nvim-treesitter",
			"ravitemer/mcphub.nvim",
			{
				"MeanderingProgrammer/render-markdown.nvim",
				opts = { file_types = { "markdown", "Avante" } },
				ft = { "markdown", "Avante" },
			},
			{
				"HakonHarnes/img-clip.nvim",
				opts = {
					default = {
						embed_image_as_base64 = false,
						prompt_for_file_name = false,
						drag_and_drop = { insert_mode = true },
						use_absolute_path = true,
					},
				},
			},
		},
		cmd = {
			"AvanteAsk",
			"AvanteChat",
			"AvanteToggle",
			"AvanteEdit",
		},
		keys = {
			{ "<leader>a", "", desc = "+ai", mode = { "n", "v" } },
			{ "<leader>aa", "<cmd>AvanteAsk<cr>", desc = "Ask", mode = { "n", "v" } },
			{ "<leader>ac", "<cmd>AvanteToggle<cr>", desc = "Toggle Chat", mode = { "n", "v" } },
			{ "<leader>ai", "<cmd>AvanteEdit<cr>", desc = "Edit", mode = "v" },
			{ "<leader>an", "<cmd>AvanteChat<cr>", desc = "New Chat", mode = { "n", "v" } },
		},
		init = function()
			-- Auto-open on blank nvim start, waiting for mcphub to be ready
			vim.api.nvim_create_autocmd("VimEnter", {
				once = true,
				callback = function()
					if vim.fn.argc(-1) > 0 then
						return
					end
					if vim.api.nvim_buf_line_count(0) > 1 or vim.fn.getline(1) ~= "" then
						return
					end
					local function try_open(n)
						if n <= 0 then
							return
						end
						local hub = pcall(require, "mcphub") and require("mcphub").get_hub_instance()
						if hub and hub:ensure_ready() then
							vim.cmd("AvanteChat")
						else
							vim.defer_fn(function()
								try_open(n - 1)
							end, 200)
						end
					end
					vim.schedule(function()
						try_open(50)
					end)
				end,
			})

			-- Once mcphub is ready, push its SSE endpoint into the ACP provider config
			-- so Claude Code gets full MCP access in the ACP session.
			-- We poll because mcphub fires no reliable autocmd for readiness.
			local function try_inject_mcp(n)
				if n <= 0 then
					return
				end
				local hub = pcall(require, "mcphub") and require("mcphub").get_hub_instance()
				if hub and hub:ensure_ready() then
					local ok, cfg = pcall(require, "avante.config")
					if ok and cfg.acp_providers and cfg.acp_providers["claude-code"] then
						cfg.acp_providers["claude-code"].mcp_servers = {
							{
								type = "sse",
								name = "mcphub",
								url = ("http://localhost:%d/mcp"):format(hub.port),
								headers = {},
							},
						}
					end
				else
					vim.defer_fn(function()
						try_inject_mcp(n - 1)
					end, 200)
				end
			end
			vim.schedule(function()
				try_inject_mcp(75)
			end)
		end,
		opts = {
			provider = "claude-code",
			acp_providers = {
				["claude-code"] = {
					command = vim.fn.expand("~/.nvm/versions/node/v22.17.0/bin/node"),
					args = {
						vim.fn.expand(
							"~/.nvm/versions/node/v22.17.0/lib/node_modules/@agentclientprotocol/claude-agent-acp/dist/index.js"
						),
					},
					env = {
						CLAUDE_CODE_EXECUTABLE = vim.fn.expand("~/.local/bin/claude"),
					},
					mcp_servers = {}, -- populated after mcphub is ready (see init)
				},
			},
			system_prompt = "When spawning agents to complete tasks, never use run_in_background. Always run agents synchronously so results appear directly in this conversation.",
			windows = {
				position = "right",
				width = 40,
			},
			behaviour = {
				acp_follow_agent_locations = true,
				auto_add_current_file = false,
			},
		},
	},
}
