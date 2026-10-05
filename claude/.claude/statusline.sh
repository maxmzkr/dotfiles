#!/bin/sh
# Status line for Claude Code: context usage, plus just enough to say where you are.
# stdin is the status JSON documented at code.claude.com/docs/en/statusline.

jq -rj '
  def unit:
    if . >= 1000000 then "\(((. / 100000) | round) / 10)M"
    elif . >= 1000 then "\((. / 1000) | round)k"
    else "\(.)" end;

  def dim: "[2m" + . + "[0m";

  # Green under half full, yellow past that, red once compaction is in sight.
  def pct_color: if . < 50 then "32" elif . < 80 then "33" else "31" end;

  (.workspace.current_dir | sub("^" + env.HOME; "~")) as $dir
  | .context_window as $c
  | ($dir | dim) + "  " + (.model.display_name | dim) + "  "
  + (if $c.used_percentage == null then ("ctx --" | dim)
     else "[\($c.used_percentage | pct_color)mctx \($c.used_percentage | round)%[0m"
          + " " + ("\($c.total_input_tokens | unit)/\($c.context_window_size | unit)" | dim)
     end)
'
