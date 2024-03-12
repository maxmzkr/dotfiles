return {
  {
    "nvim-telescope/telescope.nvim",
    dependencies = {
      {
        "nvim-telescope/telescope-live-grep-args.nvim",
        keys = {
          {
            "<leader>/",
            function()
              require("telescope").extensions.live_grep_args.live_grep_args()
            end,
            desc = "Grep (root dir)",
          },
          {
            "<leader>sg",
            function()
              require("telescope").extensions.live_grep_args.live_grep_args()
            end,
            desc = "Grep (root dir)",
          },
          {
            "<leader>sG",
            function()
              require("telescope").extensions.live_grep_args.live_grep_args({ cwd = false })
            end,
            desc = "Grep (cwd)",
          },
        },
      },
    },
    config = function()
      require("telescope").load_extension("live_grep_args")
    end,
  },
}
