return {
	-- disable gofumpt
	{
		"neovim/nvim-lspconfig",
		opts = {
			servers = {
				gopls = {
					settings = {
						gopls = {
							gofumpt = false,
						},
					},
				},
			},
		},
	},
	-- {
	-- 	"nvimtools/none-ls.nvim",
	-- 	opts = function(_, opts)
	-- 		local nls = require("null-ls")
	-- 		opts.sources = vim.tbl_filter(function(source)
	-- 			return source.name ~= nls.builtins.formatting.gofumpt.name
	-- 				and source.name ~= nls.builtins.formatting.goimports.name
	-- 		end, opts.sources or {})
	-- 		-- add golangci-lint
	-- 		table.insert(
	-- 			opts.sources,
	-- 			nls.builtins.diagnostics.golangci_lint.with({
	-- 				extra_args = function(params)
	-- 					-- disable govet because gopls has "all the usual bug-finding analyzers from the go vet suite"
	-- 					-- disable staticcheck because "In addition, gopls includes the staticcheck suite"
	-- 					-- https://github.com/golang/tools/blob/master/gopls/doc/analyzers.md
	-- 					-- run golangci-lint only on the current package because it's slow on the full project
	-- 					return { "-D", "govet", "-D", "staticcheck", vim.fs.dirname(params.bufname) }
	-- 				end,
	-- 				filter = function(diagnostic)
	-- 					-- Ignore typecheck. It cannot be disabled in golangci-lint
	-- 					-- https://github.com/golangci/golangci-lint/issues/2912
	-- 					-- typecheck only outputs errors that are already caught by gopls
	-- 					return diagnostic.source ~= "golangci-lint: typecheck"
	-- 				end,
	-- 			})
	-- 		)
	-- 		-- This runs on the full directory instead of the current file
	-- 		-- table.insert(opts.sources, nls.builtins.diagnostics.codespell)
	-- 		opts.debug = true
	-- 	end,
	-- },
	{
		"stevearc/conform.nvim",
		opts = function(_, opts)
			opts.formatters_by_ft.go = vim.tbl_filter(function(formatter)
				-- disable goimports because it's default config times it out too quick
				-- disable gofumpt because we're doing that in gopls
				return formatter ~= "goimports" and formatter ~= "gofumpt"
			end, opts.formatters_by_ft.go or {})
			-- table.insert(opts.formatters_by_ft.go, "golines")
		end,
	},
	-- working on a way to apply formatting only to changed lines
	-- {
	-- 	"stevearc/conform.nvim",
	-- 	opts = {
	-- 		log_level = vim.log.levels.DEBUG,
	-- 		formatters = {
	-- 			golines = function(bufnr)
	-- 				local hunks = require("gitsigns").get_hunks(bufnr)
	-- 				if hunks == nil then
	-- 					return
	-- 				end

	-- 				local args = { vim.api.nvim_buf_get_name(bufnr) }
	-- 				local function append_range()
	-- 					if next(hunks) == nil then
	-- 						return
	-- 					end
	-- 					local hunk = nil
	-- 					while next(hunks) ~= nil and (hunk == nil or hunk.type == "delete") do
	-- 						hunk = table.remove(hunks)
	-- 					end

	-- 					if hunk ~= nil and hunk.type ~= "delete" then
	-- 						local start = hunk.added.start
	-- 						local last = start + hunk.added.count
	-- 						table.insert(args, start .. ":" .. last)
	-- 						append_range()
	-- 					end
	-- 				end
	-- 				append_range()

	-- 				return {
	-- 					command = "/home/max/pipeline/diff_filter.sh",
	-- 					args = args,
	-- 				}
	-- 			end,
	-- 		},
	-- 	},
	-- },
	-- {
	-- 	"williamboman/mason.nvim",
	-- 	opts = { ensure_installed = { "sonarlint-language-server" } },
	-- },
	-- working on getting sonarlint running
	-- {
	-- 	"neovim/nvim-lspconfig",
	-- 	init = function()
	-- 		local sonar_language_server_path =
	-- 			require("mason-registry").get_package("sonarlint-language-server"):get_install_path()

	-- 		local analyzers_path = sonar_language_server_path .. "/extension/analyzers"

	-- 		require("lspconfig.configs").sonarqube = {
	-- 			default_config = {
	-- 				cmd = {
	-- 					sonar_language_server_path .. "/sonarlint-language-server",
	-- 					"-stdio",
	-- 					"-analyzers",
	-- 					vim.fn.expand(analyzers_path .. "/sonargo.jar"),
	-- 				},
	-- 				filetypes = { "go" },
	-- 				root_dir = function(fname)
	-- 					return require("lspconfig.util").root_pattern(
	-- 						"sonar-project.properties",
	-- 						"scan-project.properties"
	-- 					)(fname)
	-- 				end,
	-- 			},
	-- 		}

	-- 		require("lspconfig").sonarqube.setup({})
	-- 	end,
	-- },
	-- {
	-- 	"https://gitlab.com/schrieveslaach/sonarlint.nvim",
	-- 	opts = function(params, opts)
	-- 		opts.server = {
	-- 			cmd = {
	-- 				"/usr/lib/jvm/java-21-openjdk-amd64/bin/java",
	-- 				"-jar",
	-- 				require("mason-registry").get_package("sonarlint-language-server"):get_install_path()
	-- 					.. "/extension/server/sonarlint-ls.jar",
	-- 				"-stdio",
	-- 				"-analyzers",
	-- 				require("mason-registry").get_package("sonarlint-language-server"):get_install_path()
	-- 					.. "/extension/analyzers/sonargo.jar",
	-- 			},
	-- 			cmd_cwd = "/home/max/pipeline/services/collections",
	-- 			cmd_env = {
	-- 				JENV_DIR = "/home/max/pipeline/services/collections",
	-- 			},
	-- 			before_init = function(_, config)
	-- 				config.cmd_cwd = "/home/max/pipeline/services/collections"
	-- 				config.cmd_env = {
	-- 					JENV_DIR = "/home/max/pipeline/services/collections",
	-- 				}
	-- 			end,
	-- 		}
	-- 		opts.filetypes = { "go" }
	-- 	end,
	-- 	ft = { "go" },
	-- },
}
