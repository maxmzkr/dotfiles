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

-- Track nvim's focus state so the CodeCompanion-done notifier can skip
-- setting the tmux flag when we're already watching, and clear it when
-- focus returns.
vim.g.cc_focused = true
vim.api.nvim_create_autocmd({ "FocusGained", "FocusLost" }, {
	group = augroup("codecompanion_focus_track"),
	callback = function(args)
		vim.g.cc_focused = args.event == "FocusGained"
		if args.event == "FocusGained" then
			local pane = os.getenv("TMUX_PANE")
			if pane then
				vim.system({ "tmux", "set-option", "-u", "-t", pane, "@cc_done" }, { detach = true })
			end
		end
	end,
})

-- Play a sound when CodeCompanion finishes responding, and flag the tmux
-- session (only if nvim isn't currently focused) so other sessions can
-- see at a glance which one finished.
vim.api.nvim_create_autocmd("User", {
	group = augroup("codecompanion_done_notify"),
	pattern = { "CodeCompanionChatDone", "CodeCompanionRequestFinished" },
	callback = function(args)
		vim.system({ "paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga" }, { detach = true })
		if args.match == "CodeCompanionChatDone" and not vim.g.cc_focused then
			local pane = os.getenv("TMUX_PANE")
			if pane then
				vim.system({ "tmux", "set-option", "-t", pane, "@cc_done", "1" }, { detach = true })
			end
		end
	end,
})
-- Prevent LSP clients (gopls etc.) from attaching to octo:// buffers.
-- LspAttach fires after textDocument/didOpen is already sent, which is too late —
-- gopls rejects the non-file URI before our detach runs. Intercept at the source.
do
	local orig = vim.lsp.buf_attach_client
	vim.lsp.buf_attach_client = function(bufnr, client_id)
		if vim.api.nvim_buf_get_name(bufnr):match("^octo://") then
			return false
		end
		return orig(bufnr, client_id)
	end
end

-- In CodeCompanion chat buffers, <leader>gf opens the file under the cursor
-- in another split (preferring the previously-active window) instead of the
-- chat split itself.
vim.api.nvim_create_autocmd("FileType", {
	group = augroup("codecompanion_gf"),
	pattern = { "codecompanion" },
	callback = function(args)
		vim.keymap.set("n", "<leader>gf", function()
			local cfile = vim.fn.expand("<cfile>")
			if cfile == "" then
				vim.notify("no file under cursor", vim.log.levels.WARN)
				return
			end

			local cur = vim.api.nvim_get_current_win()
			local prev = vim.fn.win_getid(vim.fn.winnr("#"))
			local target
			if
				prev ~= 0
				and prev ~= cur
				and vim.api.nvim_win_is_valid(prev)
				and vim.api.nvim_win_get_config(prev).relative == ""
			then
				target = prev
			else
				for _, win in ipairs(vim.api.nvim_tabpage_list_wins(0)) do
					if win ~= cur and vim.api.nvim_win_get_config(win).relative == "" then
						target = win
						break
					end
				end
			end

			if target then
				vim.api.nvim_set_current_win(target)
			else
				vim.cmd("vsplit")
			end
			vim.cmd("edit " .. vim.fn.fnameescape(cfile))
		end, { buffer = args.buf, desc = "Open file under cursor in other split" })
	end,
})

-- Re-do the clipboard write for OSC 52 from a :terminal buffer. nvim decodes
-- the payload but hands the system clipboard Vim's *internal* register form,
-- where a line break is a NUL byte -- so a multi-line copy arrives
-- NUL-separated and every consumer stops at the first one. Byte counts match
-- end to end, which is what makes it look like nothing is wrong until you
-- paste. Measured on v0.13.0-dev-602: identical at 200B and 20KB, so it is not
-- a payload limit.
--
-- This bites claude in sidekick specifically, because that is the one place it
-- copies over OSC 52 at all: on a local session it shells out to wl-copy
-- itself, and plugins/sidekick.lua clears TMUX so the sequence goes out
-- unwrapped (see the note there for what the DCS-wrapped version does to the
-- screen). So the selection you drag in claude pastes as its first line only.
--
-- tmux-copy rather than wl-copy directly: it picks the backend from whichever
-- display server the attached tmux client is using, which is the same reason
-- .tmux.conf pipes through it instead of hardcoding one.
vim.api.nvim_create_autocmd("TermRequest", {
	group = augroup("osc52_clipboard_repair"),
	callback = function(ev)
		local sequence = (ev.data and ev.data.sequence) or vim.v.termrequest or ""
		-- OSC 52 is `ESC ] 52 ; <targets> ; <base64> <terminator>`. Only the
		-- clipboard write is interesting; a `?` payload is a read request.
		local encoded = sequence:match("^\27%]52;[^;]*;(.*)$")
		if not encoded or encoded == "?" then
			return
		end
		-- BEL, ST, or a bare ESC depending on who emitted it.
		encoded = encoded:gsub("\27\\$", ""):gsub("[\7\27]+$", "")

		local ok, text = pcall(vim.base64.decode, encoded)
		if not ok or text == "" then
			return
		end

		vim.fn.system({ vim.fn.expand("~/.local/bin/tmux-copy") }, text)
	end,
})
