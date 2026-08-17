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
			-- no Copilot subscription; NES rides on the Copilot LSP, so keep it off
			nes = { enabled = false },
			cli = {
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
