# Worktree Management Scripts

Scripts to streamline git worktree workflows with tmux and nvim.

## Scripts

### `worktree-tmux` (alias: `wt`)
Create a new git worktree and open it in a tmux session with nvim.

**Usage:**
```bash
wt feature/my-branch
```

Creates:
- Worktree at `~/worktrees/<repo>/<branch>` based on `main` (or `master`)
- Tmux session named after the branch
- Opens nvim automatically

### `worktree-switch` (alias: `wts`)
Switch to an existing worktree in a tmux session. Uses `git worktree list` to find worktrees in the current repository.

**Usage:**
```bash
wts feature/my-branch              # Switch to branch
wts                                # List all available worktrees
```

**Note:** Must be run from within a git repository. Properly handles branch names with slashes (e.g., `feature/foo/bar`).

Both commands support tab completion for easy navigation between worktrees!

## Installation

The scripts are automatically added to PATH via `~/.zshrc.d/worktree.zsh` which is loaded by the `mattmc3/zshrc.d` plugin.

After pulling these changes:
```bash
source ~/.zshrc
```
