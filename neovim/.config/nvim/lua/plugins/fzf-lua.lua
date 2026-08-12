return {
	{
		"ibhagwan/fzf-lua",
		opts = function(_, opts)
			-- `live_grep` normalizes against the `grep` namespace, so this covers both.
			return vim.tbl_deep_extend("force", opts or {}, {
				grep = {
					-- Live path filtering: everything after " -- " narrows by path while the
					-- part before it keeps going to rg as the content pattern.
					--
					-- NOTE: in multiprocess mode fzf-lua ships this to its headless child as
					-- a `string.dump`, which drops upvalues — so it must stay self-contained.
					rg_glob_fn = function(query, o)
						local search, filter = query:match("(.*)" .. (o.glob_separator or "%s%-%-") .. "(.*)")
						if not search then
							return query, nil
						end
						local shellescape = require("fzf-lua.libuv").shellescape
						local args, globs = {}, {}
						for _, token in ipairs(vim.split(filter or "", "%s+", { trimempty = true })) do
							local neg, body = token:match("^(!?)(.*)$")
							local pats = {}
							if #body == 0 then
								pats = {}
							elseif body:find("[*?%[]") then
								pats = { body } -- already a glob, pass through
							elseif body:sub(1, 1) == "." then
								pats = { "**/*" .. body } -- extension: ".go"
							else
								-- substring match on the path; "/" anchors segment order
								local seq = body:gsub("/+", "*/*")
								pats = { "**/*" .. seq .. "*", "**/*" .. seq .. "*/**" }
							end
							for _, p in ipairs(pats) do
								globs[#globs + 1] = neg .. p
								args[#args + 1] = ("%s %s"):format(o.glob_flag or "--iglob", shellescape(neg .. p))
							end
						end
						return search, #args > 0 and (table.concat(args, " ") .. " ") or nil, globs
					end,
				},
			})
		end,
	},
}
