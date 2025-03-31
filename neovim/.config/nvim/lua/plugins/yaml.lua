return {
	{
		"neovim/nvim-lspconfig",
		opts = {
			-- make sure mason installs the server
			servers = {
				yamlls = {
					settings = {
						yaml = {
							format = {
								enable = false,
							},
							validate = true,
							schemas = {
								["file:///home/max/.config/nvim/values.schema.json"] = "development.values.yaml"
							},
						},
					},
					capabilities = vim.tbl_deep_extend(
						"force",
						vim.lsp.protocol.make_client_capabilities(),
						{
							workspace = {
								didChangeConfiguration = {
									dynamicRegistration = true
								}
							}
						}
					),
				},
			},
		},
	},
}
