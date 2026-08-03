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
						},
					},
				},
			},
		},
		keys = {
			{
				"<leader>aa",
				function()
					require("sidekick.cli").toggle({ name = "claude", filter = { cwd = true }, focus = true })
				end,
				desc = "Toggle Claude (subscription)",
				mode = { "n", "v" },
			},
			{
				"<leader>ab",
				function()
					require("sidekick.cli").toggle({ name = "claude-bifrost", filter = { cwd = true }, focus = true })
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
						require("sidekick.cli").toggle({ name = "claude", filter = { cwd = true }, focus = true })
					end)
				end,
			})
		end,
	},
}
