"""Toggle the Claude session sidebar as a fixed-width column on the left of the tab.

Mapped in kitty.conf. Runs inside kitty (no_ui), so it needs no remote control.
The sidebar is handed the tty of the window it was opened from: that is the tty
the tmux client in that window runs on, so clicks switch this window's client and
not whichever one tmux considers most recent.
"""

import os

from kittens.tui.handler import result_handler
from kitty.constants import config_dir

MARK = "claude_sidebar"
WIDTH = 28


def main(args):
    pass


def tty_of(window):
    try:
        return os.readlink(f"/proc/{window.child.pid}/fd/0")
    except OSError:
        return ""


@result_handler(no_ui=True)
def handle_result(args, answer, target_window_id, boss):
    tab = boss.active_tab
    target = boss.window_id_map.get(target_window_id)
    if tab is None or target is None:
        return

    for window in tab.windows:
        if window.user_vars.get(MARK):
            boss.mark_window_for_close(window)
            return

    if tab.current_layout.name != "splits":
        tab.goto_layout("splits")
    boss.call_remote_control(
        target,
        (
            "launch",
            f"--var={MARK}=1",
            "--title=claude",
            "--location=vsplit",
            # Splits bias is the new window's share of the target's width.
            f"--bias={max(1, min(50, round(WIDTH * 100 / max(1, target.screen.columns))))}",
            f"--env=CLAUDE_SIDEBAR_TTY={tty_of(target)}",
            "python3",
            os.path.join(config_dir, "claude_sidebar", "sidebar.py"),
        ),
    )
    sidebar = next((w for w in tab.windows if w.user_vars.get(MARK)), None)
    if sidebar is None:
        return
    boss.call_remote_control(
        sidebar, ("action", f"--match=id:{sidebar.id}", "layout_action", "move_to_screen_edge", "left")
    )
    boss.set_active_window(target)
