-- Strip // and /* */ comments so JSONC files parse. VSCode allows them; vim.json.decode does not.
local function strip_jsonc(s)
	s = s:gsub("/%*.-%*/", "")
	local out = {}
	for line in (s .. "\n"):gmatch("([^\n]*)\n") do
		local stripped = line:gsub("^(%s*)//.*$", "%1"):gsub("([^:])//.*$", "%1")
		table.insert(out, stripped)
	end
	return table.concat(out, "\n")
end

local function read_vscode_yaml_schemas(root_dir)
	if not root_dir then
		return nil
	end
	local path = root_dir .. "/.vscode/settings.json"
	local f = io.open(path, "r")
	if not f then
		return nil
	end
	local content = f:read("*a")
	f:close()
	local ok, decoded = pcall(vim.json.decode, strip_jsonc(content))
	if not ok or type(decoded) ~= "table" then
		return nil
	end
	return decoded["yaml.schemas"]
end

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
								["file:///home/max/.config/nvim/values.schema.json"] = "development.values.yaml",
							},
						},
					},
					capabilities = vim.tbl_deep_extend(
						"force",
						vim.lsp.protocol.make_client_capabilities(),
						{
							workspace = {
								didChangeConfiguration = {
									dynamicRegistration = true,
								},
							},
						}
					),
					on_new_config = function(new_config, new_root_dir)
						local schemas = read_vscode_yaml_schemas(new_root_dir)
						if not schemas then
							return
						end
						new_config.settings = new_config.settings or {}
						new_config.settings.yaml = new_config.settings.yaml or {}
						new_config.settings.yaml.schemas = vim.tbl_extend(
							"force",
							new_config.settings.yaml.schemas or {},
							schemas
						)
					end,
				},
			},
		},
	},
}
