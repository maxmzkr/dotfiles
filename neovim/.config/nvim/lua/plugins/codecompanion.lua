local secrets = (function()
	local path = vim.fn.expand("~/.config/bifrost/credentials.json")
	local ok, data = pcall(vim.fn.readfile, path)
	if not ok then return {} end
	return vim.fn.json_decode(table.concat(data, "\n")) or {}
end)()

return {
	{
		"olimorris/codecompanion.nvim",
		version = "^19",
		dependencies = {
			"nvim-lua/plenary.nvim",
			"nvim-treesitter/nvim-treesitter",
			"ravitemer/mcphub.nvim",
			"ravitemer/codecompanion-history.nvim",
			{
				"MeanderingProgrammer/render-markdown.nvim",
				ft = { "markdown", "codecompanion" },
				opts = { file_types = { "markdown", "codecompanion" } },
			},
			{
				"HakonHarnes/img-clip.nvim",
				opts = {
					filetypes = {
						codecompanion = {
							prompt_for_file_name = false,
							template = "[Image]($FILE_PATH)",
							use_absolute_path = true,
						},
					},
				},
			},
		},
		cmd = {
			"CodeCompanion",
			"CodeCompanionChat",
			"CodeCompanionActions",
			"CodeCompanionCmd",
			"CodeCompanionCLI",
		},
		keys = {
			{ "<leader>a", "", desc = "+ai", mode = { "n", "v" } },
			{ "<leader>aa", "<cmd>CodeCompanionActions<cr>", desc = "Actions", mode = { "n", "v" } },
			{ "<leader>ac", "<cmd>CodeCompanionChat Toggle<cr>", desc = "Toggle Chat", mode = { "n", "v" } },
			{ "<leader>an", "<cmd>CodeCompanionChat<cr>", desc = "New Chat", mode = { "n", "v" } },
			{ "<leader>ai", ":CodeCompanion ", desc = "Inline", mode = { "n", "v" } },
			{ "<leader>ad", "<cmd>CodeCompanionCmd<cr>", desc = "Cmd-line", mode = "n" },
			{ "<leader>al", "<cmd>CodeCompanionCLI<cr>", desc = "CLI (Claude Code)", mode = { "n", "v" } },
			{ "ga", "<cmd>CodeCompanionChat Add<cr>", desc = "Add to Chat", mode = "v" },
		},
		init = function()
			vim.cmd([[cab cc CodeCompanion]])
			if secrets.api_key then vim.env.ANTHROPIC_API_KEY = secrets.api_key end
			if secrets.url then vim.env.ANTHROPIC_BASE_URL = secrets.url end
			vim.api.nvim_create_autocmd("VimEnter", {
				once = true,
				callback = function()
					-- Only auto-open chat when nvim is launched blank — skip git commit,
					-- piped stdin, opening a file, etc.
					if vim.fn.argc(-1) > 0 then return end
					if vim.api.nvim_buf_line_count(0) > 1 or vim.fn.getline(1) ~= "" then return end
					vim.schedule(function()
						if vim.fn.exists(":CodeCompanionChat") == 2 then
							vim.cmd("CodeCompanionChat")
						end
					end)
				end,
			})
		end,
		opts = {
			adapters = {
				http = {
					-- Inline/chat HTTP traffic → Bifrost
					anthropic = function()
						return require("codecompanion.adapters").extend("anthropic", {
							url = secrets.url and (secrets.url .. "/v1/messages"),
							env = {
								api_key = secrets.api_key,
							},
							schema = {
								model = { default = "claude-sonnet-4-5" },
								extended_thinking = { default = true },
							},
						})
					end,
				},
				acp = {
					claude_code = function()
						return require("codecompanion.adapters").extend("claude_code", {
							commands = {
								default = { vim.fn.expand("~/.nvm/versions/node/v22.17.0/bin/node"), vim.fn.expand("~/.nvm/versions/node/v22.17.0/lib/node_modules/@agentclientprotocol/claude-agent-acp/dist/index.js") },
								yolo = { "npx", "-y", "@agentclientprotocol/claude-agent-acp", "--yolo" },
							},
							env = {
								ANTHROPIC_API_KEY = secrets.api_key,
								ANTHROPIC_BASE_URL = secrets.url,
							},
						})
					end,
				},
			},
			interactions = {
				chat = {
					adapter = "claude_code",
					roles = { user = "me", llm = "claude" },
					variables = {},
					tools = {
						["memory"] = {
							opts = {
								whitelist = {
									{
										path = (vim.fn.systemlist("git rev-parse --show-toplevel 2>/dev/null")[1] or vim.fn.getcwd()) .. "/memories",
										as = "/memories",
									},
								},
							},
						},
						opts = {
							default_tools = { "agent", "memory" },
						},
					},
					opts = {
						completion_provider = "blink", -- LazyVim default
					},
				},
				inline = {
					adapter = "claude_code",
				},
				cli = {
					agent = "claude_code",
				},
			},
			display = {
				action_palette = {
					provider = "default",
				},
				chat = {
					window = {
						layout = "vertical",
						position = "right",
						width = 0.40,
					},
					show_settings = false,
					show_token_count = true,
					intro_message = "Welcome! Press ? for keymaps.",
				},
				diff = {
					enabled = true,
					provider = "default",
				},
			},
			extensions = {
				history = {
					enabled = true,
					opts = {
						auto_save = true,
						picker = "snacks",
						continue_last_chat = false,
					},
				},
				mcphub = {
					callback = "mcphub.extensions.codecompanion",
					opts = {
						show_result_in_chat = true,
						make_vars = true,
						make_slash_commands = true,
					},
				},
			},
			opts = {
				log_level = "DEBUG",
				language = "English",
			},
		},
	},
}
