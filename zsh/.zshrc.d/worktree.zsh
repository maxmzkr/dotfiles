# Worktree management aliases and completion
# This file is sourced by .zshrc

# Add completions directory to fpath BEFORE compinit
fpath=(~/.config/zsh/completions $fpath)

# Add local bin to PATH if not already there
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Alias
alias wt='worktree-tmux'
