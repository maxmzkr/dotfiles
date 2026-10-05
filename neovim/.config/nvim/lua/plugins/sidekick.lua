-- Read the Bifrost proxy credentials ({ api_key, url }) written by the corp
-- tooling. Returns {} if the file is missing so the bifrost tool just fails to
-- launch rather than erroring at startup.
local function bifrost_secrets()
	local path = vim.fn.expand("~/.config/bifrost/credentials.json")
	local ok, data = pcall(vim.fn.readfile, path)
	if not ok then
		return {}
	end
	return vim.fn.json_decode(table.concat(data, "\n")) or {}
end

local secrets = bifrost_secrets()

return {
	{
		"folke/sidekick.nvim",
		opts = {
			-- NES is left at its default (enabled). It rides on the Copilot LSP's
			-- `textDocument/copilotInlineEdit`, a GitHub-only method, so it needs a
			-- Copilot entitlement -- the free tier covers it. LazyVim's ai.sidekick
			-- extra registers `servers.copilot` only when nes.enabled is not false,
			-- and that registration is what makes mason install
			-- copilot-language-server. Setting it back to false silently uninstalls
			-- the server, so this stays absent rather than being written out as true.
			--
			-- copilot.lua stays disabled in copilot.lua: it bundles its own copy of
			-- the same LSP and would displace the lspconfig-managed one, and its
			-- inline ghost text isn't wanted -- NES is the whole point here.
			cli = {
				win = {
					keys = {
						-- Sidekick's buffer picker defaults to `<c-b>` in mode "nt",
						-- so in the terminal it swallows the key before claude sees
						-- it. Claude binds `<c-b>` itself (run the current tool call
						-- in the background), and a buffer picker is reachable from
						-- any other window; the picker stays on `<c-b>` in normal
						-- mode, where nothing competes for it.
						buffers = { mode = "n" },
					},
				},
				tools = {
					-- Regular Claude on my Anthropic subscription. The ambient
					-- environment sometimes carries Bifrost's ANTHROPIC_* vars
					-- (source unknown), so clear them explicitly (= false) to force
					-- the oauth creds in ~/.claude/.credentials.json.
					claude = {
						env = {
							ANTHROPIC_BASE_URL = false,
							ANTHROPIC_API_KEY = false,
							ANTHROPIC_AUTH_TOKEN = false,
							-- See TMUX note below.
							TMUX = false,
							TMUX_PANE = false,
							CLAUDE_TMUX_PANE = vim.env.TMUX_PANE,
						},
					},
					-- Same claude binary, routed through the Bifrost proxy. Use when
					-- the subscription runs out of credits.
					["claude-bifrost"] = {
						cmd = { "claude" },
						env = {
							ANTHROPIC_BASE_URL = secrets.url,
							ANTHROPIC_API_KEY = secrets.api_key,
							ANTHROPIC_AUTH_TOKEN = false,
							TMUX = false,
							TMUX_PANE = false,
							CLAUDE_TMUX_PANE = vim.env.TMUX_PANE,
						},
					},
					-- TMUX/TMUX_PANE are cleared because nvim runs inside tmux and the
					-- vars would be inherited, but the terminal claude actually talks to
					-- is nvim's own emulator. Claude enables mouse tracking (1003+SGR)
					-- and does its own selection, then copies with OSC 52 — wrapped in
					-- tmux's `ESC P tmux; ...` DCS passthrough when it thinks it's under
					-- tmux. libvterm doesn't unwrap that, so the doubled ESC breaks the
					-- parse and `52;c;<base64 of the selection>` gets painted over the
					-- input box until the next full redraw. Unset, claude emits plain
					-- OSC 52, which nvim's terminal does understand and turns into a
					-- real clipboard write. Enabling `cli.mux.backend` would put claude
					-- in an actual tmux pane and this would have to go.
					--
					-- CLAUDE_TMUX_PANE carries the pane id back in under a name nothing
					-- but the waiting-notifier hooks in ~/.claude/settings.json reads, so
					-- the status-right marker still lights up for nvim-hosted sessions
					-- without claude believing it is under tmux. It is nil when nvim
					-- itself is not in tmux, which just leaves the var unset. With TMUX
					-- cleared too, `tmux set-option` talks to the default socket rather
					-- than the inherited one — fine with a single tmux server.
				},
			},
		},
		keys = {
			{
				"<leader>aa",
				function()
					-- No `filter = { cwd = true }`. That filter only matches tools that
					-- already have a running session in this cwd (state.lua `is()`
					-- requires `t.session`), so with nothing running it matches zero
					-- tools and warns "No tools match the given filter" instead of
					-- starting one.
					require("sidekick.cli").toggle({ name = "claude", focus = true })
				end,
				desc = "Toggle Claude (subscription)",
				mode = { "n", "v" },
			},
			{
				"<leader>ab",
				function()
					require("sidekick.cli").toggle({ name = "claude-bifrost", focus = true })
				end,
				desc = "Toggle Claude (Bifrost proxy)",
				mode = { "n", "v" },
			},
			{
				"<leader>ac",
				function()
					require("sidekick.cli").toggle()
				end,
				desc = "Toggle AI CLI",
				mode = { "n", "v" },
			},
		},
		init = function()
			vim.api.nvim_create_autocmd("VimEnter", {
				once = true,
				callback = function()
					-- Only auto-open Claude when nvim is launched blank — skip git commit,
					-- piped stdin, opening a file, etc.
					if vim.fn.argc(-1) > 0 then
						return
					end
					if vim.api.nvim_buf_line_count(0) > 1 or vim.fn.getline(1) ~= "" then
						return
					end
					vim.schedule(function()
						require("sidekick.cli").toggle({ name = "claude", focus = true })
					end)
				end,
			})
		end,
	},
}
