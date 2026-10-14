-- Find the current chat buffer's bufnr, if any
local function chat_bufnr()
  local ok, cc = pcall(require, "codecompanion")
  if not ok then return nil end
  local chat = cc.last_chat and cc.last_chat()
  if chat and chat.bufnr and vim.api.nvim_buf_is_valid(chat.bufnr) then return chat.bufnr end
end

local function open_chat_in_current_tab()
  local bufnr = chat_bufnr()
  if not bufnr then return end
  -- Skip if the chat is already visible in this tab
  for _, win in ipairs(vim.api.nvim_tabpage_list_wins(0)) do
    if vim.api.nvim_win_get_buf(win) == bufnr then return end
  end
  local cfg = require("codecompanion.config").display.chat.window
  local position = cfg.position or "right"
  local width = cfg.width or 0.40
  local cols = vim.o.columns
  local w = (width <= 1) and math.floor(cols * width) or width
  local split = (position == "left") and "topleft vertical" or "botright vertical"
  vim.cmd(("%s %dsplit"):format(split, w))
  vim.api.nvim_win_set_buf(0, bufnr)
end

-- :DiffviewOpen always makes a new tab; this re-points the current view instead.
local function set_rev(rev_arg)
  local view = require("diffview.lib").get_current_view()
  if not (view and view.left) then
    vim.notify("Not in a diffview", vim.log.levels.WARN)
    return
  end
  local opts = view.adapter:diffview_options(require("diffview.arg_parser").parse({ rev_arg }))
  if not opts then return end

  local cur = view.panel.cur_file and view.panel.cur_file.path
  -- update_files keeps entries whose path didn't change, buffers and all, so
  -- they'd go on showing the old rev. Drop them all so every file is rebuilt.
  view.panel:set_cur_file(nil)
  for _, file in view.files:iter() do
    file:destroy()
  end
  view.files:set_working({})
  view.files:set_staged({})
  view.files:set_conflicting({})

  view.left, view.right, view.options = opts.left, opts.right, opts.options
  view.rev_arg = rev_arg
  view.panel.rev_pretty_name = rev_arg
  view:update_files(function()
    if cur then view:set_file_by_path(cur) end
  end)
end

-- Re-point an open diffview (this tab's, else the first one in any tab) at a
-- prompted rev, or open one if there isn't any.
local function open_or_set_rev()
  local lib = require("diffview.lib")
  local view = lib.get_current_view()
  if not (view and view.left) then
    view = nil
    for _, v in ipairs(lib.views) do
      if v.left and vim.api.nvim_tabpage_is_valid(v.tabpage) then
        view = v
        break
      end
    end
  end
  vim.ui.input({ prompt = "Diff against: ", default = view and view.rev_arg or "HEAD~1" }, function(rev)
    if not rev then return end
    if view then
      vim.api.nvim_set_current_tabpage(view.tabpage)
      set_rev(rev ~= "" and rev or nil)
    else
      vim.cmd("DiffviewOpen " .. rev)
    end
  end)
end

return {
  {
    "sindrets/diffview.nvim",
    cmd = { "DiffviewOpen", "DiffviewClose", "DiffviewToggleFiles", "DiffviewFocusFiles", "DiffviewFileHistory" },
    config = function(_, opts)
      require("diffview").setup(opts)
      DiffviewGlobal.emitter:on("view_opened", vim.schedule_wrap(open_chat_in_current_tab))
      vim.api.nvim_create_user_command("DiffviewSetRev", function(cmd)
        set_rev(cmd.args ~= "" and cmd.args or nil)
      end, { nargs = "?", desc = "Point the current diffview at a new rev" })
    end,
    keys = {
      { "<leader>gd", "<cmd>DiffviewOpen HEAD<cr>", desc = "Diffview: vs HEAD" },
      { "<leader>gD", open_or_set_rev, desc = "Diffview: open or set rev" },
      { "<leader>gr", "<cmd>DiffviewRefresh<cr>", desc = "Diffview: refresh" },
      { "<leader>gh", "<cmd>DiffviewFileHistory<cr>", desc = "Diffview: branch history" },
      { "<leader>gH", "<cmd>DiffviewFileHistory %<cr>", desc = "Diffview: current file history" },
      { "<leader>gx", "<cmd>DiffviewClose<cr>", desc = "Diffview: close" },
    },
    opts = {
      enhanced_diff_hl = true,
      hooks = {
        -- enhanced_diff_hl recolors old-only lines, but changed words are still
        -- DiffText (green) on both sides.
        diff_buf_win_enter = function(_, _, ctx)
          if ctx.layout_name:match("^diff2") and ctx.symbol == "a" then
            vim.opt_local.winhl = table.concat({
              "DiffAdd:DiffviewDiffAddAsDelete",
              "DiffDelete:DiffviewDiffDelete",
              "DiffText:DiffviewDiffTextAsDelete",
            }, ",")
          end
        end,
      },
      view = {
        merge_tool = {
          layout = "diff3_mixed",
        },
      },
      keymaps = {
        view = {
          { "n", "<tab>", "<cmd>DiffviewToggleFiles<cr>", { desc = "Toggle file panel" } },
        },
        file_panel = {
          { "n", "<tab>", "<cmd>DiffviewToggleFiles<cr>", { desc = "Toggle file panel" } },
        },
      },
    },
  },
}
