
return {
	{
		"olimorris/codecompanion.nvim",
		enabled = false,
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
			{
				"<leader>aB",
				function()
					local chat = require("codecompanion").last_chat()
					if not chat then
						chat = require("codecompanion").chat()
					end
					if not chat then
						return vim.notify("Could not get a chat buffer", vim.log.levels.ERROR)
					end
					local cfg = require("codecompanion.config")
					local buffer_cmd = require("codecompanion.interactions.shared.slash_commands.buffer").new({
						Chat = chat,
						config = cfg.interactions.chat.slash_commands["buffer"],
					})
					local count = 0
					for _, buf in ipairs(require("codecompanion.utils.buffers").get_open()) do
						if buf.bufnr ~= chat.bufnr and buf.path ~= "" and vim.fn.filereadable(buf.path) == 1 then
							buffer_cmd:output(
								{ bufnr = buf.bufnr, name = buf.name, path = buf.path },
								{ silent = true }
							)
							count = count + 1
						end
					end
					vim.notify(("Added %d buffer(s) to chat"):format(count))
				end,
				desc = "Add all buffers to Chat",
				mode = "n",
			},
		},
		init = function()
			vim.cmd([[cab cc CodeCompanion]])
			vim.api.nvim_create_autocmd("VimEnter", {
				once = true,
				callback = function()
					-- Only auto-open chat when nvim is launched blank — skip git commit,
					-- piped stdin, opening a file, etc.
					if vim.fn.argc(-1) > 0 then
						return
					end
					if vim.api.nvim_buf_line_count(0) > 1 or vim.fn.getline(1) ~= "" then
						return
					end
					local function try_open(attempts_left)
						if attempts_left <= 0 then
							return
						end
						local hub = pcall(require, "mcphub") and require("mcphub").get_hub_instance()
						if hub and hub:ensure_ready() then
							if vim.fn.exists(":CodeCompanionChat") == 2 then
								vim.cmd("CodeCompanionChat")
							end
						else
							vim.defer_fn(function()
								try_open(attempts_left - 1)
							end, 200)
						end
					end
					vim.schedule(function()
						try_open(50)
					end) -- wait up to 10s
				end,
			})
		end,
		opts = {
			adapters = {
				http = {
					anthropic = function()
						return require("codecompanion.adapters").extend("anthropic", {
							schema = {
								model = { default = "claude-sonnet-4-6" },
								extended_thinking = { default = true },
							},
						})
					end,
					anthropic_bifrost = function()
						local secrets = (function()
							local path = vim.fn.expand("~/.config/bifrost/credentials.json")
							local ok, data = pcall(vim.fn.readfile, path)
							if not ok then
								return {}
							end
							return vim.fn.json_decode(table.concat(data, "\n")) or {}
						end)()
						return require("codecompanion.adapters").extend("anthropic", {
							url = secrets.url and (secrets.url .. "/v1/messages"),
							env = {
								api_key = secrets.api_key,
							},
							schema = {
								model = { default = "claude-sonnet-4-6" },
								extended_thinking = { default = true },
							},
						})
					end,
				},
				acp = {
					claude_code = function()
						-- Block until mcphub is ready so we can pass its aggregator endpoint
						-- to the Claude Code subprocess as a single MCP server. This way
						-- ${cmd: ...} interpolation in servers.json is resolved by mcphub,
						-- not the ACP child process.
						local instance
						local ok = vim.wait(15000, function()
							instance = require("mcphub").get_hub_instance()
							return instance and instance:ensure_ready()
						end, 100)
						local mcp_servers = {}
						if ok and instance then
							mcp_servers = {
								{
									type = "sse",
									name = "mcphub",
									url = ("http://localhost:%d/mcp"):format(instance.port),
									headers = {},
								},
							}
						else
							vim.notify("MCPHub not ready; chat opened without MCP tools", vim.log.levels.WARN)
						end
						return require("codecompanion.adapters").extend("claude_code", {
							commands = {
								default = {
									vim.fn.expand("~/.nvm/versions/node/v22.17.0/bin/node"),
									vim.fn.expand(
										"~/.nvm/versions/node/v22.17.0/lib/node_modules/@agentclientprotocol/claude-agent-acp/dist/index.js"
									),
								},
								yolo = { "npx", "-y", "@agentclientprotocol/claude-agent-acp", "--yolo" },
							},
							env = {
								CLAUDE_CODE_EXECUTABLE = vim.fn.expand("~/.local/bin/claude"),
							},
							defaults = {
								mcpServers = mcp_servers,
							},
						})
					end,
					claude_code_bifrost = function()
						local secrets = (function()
							local path = vim.fn.expand("~/.config/bifrost/credentials.json")
							local ok, data = pcall(vim.fn.readfile, path)
							if not ok then
								return {}
							end
							return vim.fn.json_decode(table.concat(data, "\n")) or {}
						end)()
						local instance
						local ok = vim.wait(15000, function()
							instance = require("mcphub").get_hub_instance()
							return instance and instance:ensure_ready()
						end, 100)
						local mcp_servers = {}
						if ok and instance then
							mcp_servers = {
								{
									type = "sse",
									name = "mcphub",
									url = ("http://localhost:%d/mcp"):format(instance.port),
									headers = {},
								},
							}
						else
							vim.notify("MCPHub not ready; chat opened without MCP tools", vim.log.levels.WARN)
						end
						return require("codecompanion.adapters").extend("claude_code", {
							commands = {
								default = {
									vim.fn.expand("~/.nvm/versions/node/v22.17.0/bin/node"),
									vim.fn.expand(
										"~/.nvm/versions/node/v22.17.0/lib/node_modules/@agentclientprotocol/claude-agent-acp/dist/index.js"
									),
								},
								yolo = { "npx", "-y", "@agentclientprotocol/claude-agent-acp", "--yolo" },
							},
							env = {
								ANTHROPIC_API_KEY = secrets.api_key,
								ANTHROPIC_BASE_URL = secrets.url,
							},
							defaults = {
								mcpServers = mcp_servers,
							},
						})
					end,
				},
			},
			interactions = {
				chat = {
					adapter = "claude_code",
					roles = { user = "me", llm = "claude" },
					system_prompt = "When spawning agents to complete tasks, never use run_in_background. Always run agents synchronously so results appear directly in this conversation.",
					variables = {},
					tools = {
						["memory"] = {
							opts = {
								whitelist = {
									{
										path = (
											vim.fn.systemlist("git rev-parse --show-toplevel 2>/dev/null")[1]
											or vim.fn.getcwd()
										) .. "/memories",
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
