return {
  {
    "mfussenegger/nvim-dap-python",
    keys = {
      {
        "<leader>dn",
        function()
          require("dap-python").test_method()
        end,
        desc = "Run test method under cursor",
      },
      {
        "<leader>df",
        function()
          require("dap-python").test_class()
        end,
        desc = "Run test class under cursor",
      },
      {
        "<leader>ds",
        function()
          require("dap-python").debug_selection()
        end,
        desc = "Debug the selected code",
      },
    },
  },
}
