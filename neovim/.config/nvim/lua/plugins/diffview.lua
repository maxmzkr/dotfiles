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

return {
  {
    "sindrets/diffview.nvim",
    cmd = { "DiffviewOpen", "DiffviewClose", "DiffviewToggleFiles", "DiffviewFocusFiles", "DiffviewFileHistory" },
    config = function(_, opts)
      require("diffview").setup(opts)
      DiffviewGlobal.emitter:on("view_opened", vim.schedule_wrap(open_chat_in_current_tab))
    end,
    keys = {
      { "<leader>gd", "<cmd>DiffviewOpen<cr>", desc = "Diffview: working tree" },
      { "<leader>gD", "<cmd>DiffviewOpen HEAD~1<cr>", desc = "Diffview: vs HEAD~1" },
      { "<leader>gh", "<cmd>DiffviewFileHistory<cr>", desc = "Diffview: branch history" },
      { "<leader>gH", "<cmd>DiffviewFileHistory %<cr>", desc = "Diffview: current file history" },
      { "<leader>gx", "<cmd>DiffviewClose<cr>", desc = "Diffview: close" },
    },
    opts = {
      enhanced_diff_hl = false,
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
