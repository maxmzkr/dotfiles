#!/usr/bin/env python3
"""A column listing every Claude Code instance running in tmux, by state.

State comes from two pane options that Claude Code's hooks set on their own pane
(see ~/.claude/settings.json): @claude_state and @claude_since. One `tmux
list-panes -a` per second is the whole data source.

Right-click a row (or select it and press r) to mark it read: it goes to idle
without switching to it.

Clicking a row (or j/k + Enter) switches the tmux client on CLAUDE_SIDEBAR_TTY to
that pane. toggle.py sets it to the tty of the kitty window the sidebar was opened
beside, which is the tty its tmux client runs on; without it, tmux picks the most
recently active client.
"""

import curses
import locale
import os
import select
import subprocess
import sys
import time
from dataclasses import dataclass

# Symbol and sort rank. Read (idle) sorts first -- ready for the next prompt --
# then what needs you, then what is still running.
STATES = {
    "idle": ("·", 0),
    "permission": ("⚠", 1),
    "done": ("✓", 2),
    "working": ("⋯", 3),
}

FORMAT = "\t".join(
    [
        "#{pane_id}",
        "#{session_name}",
        "#{@claude_state}",
        "#{@claude_since}",
    ]
)

LABEL_PREFIX = "maxmzkr-"


@dataclass(frozen=True)
class Row:
    pane: str
    session: str
    state: str
    since: int


def parse(output):
    rows = []
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 4 or fields[2] not in STATES:
            continue
        pane, session, state, since = fields
        rows.append(Row(pane, session, state, int(since) if since.isdigit() else 0))
    return rows


def order(rows):
    # Oldest first within a state: whatever has waited longest is on top.
    return sorted(rows, key=lambda r: (STATES[r.state][1], r.since))


def label(session):
    return session[len(LABEL_PREFIX) :] if session.startswith(LABEL_PREFIX) else session


def age(seconds):
    seconds = max(0, seconds)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{seconds // size}{unit}"
    return f"{seconds}s"


def line(row, now, width):
    """Symbol and name on the left, time in state flush right, exactly width wide.

    The name gives way to the age when they don't both fit.
    """
    right = f" {age(now - row.since)}" if row.since else ""
    left = f"{STATES[row.state][0]} {label(row.session)}"[: max(0, width - len(right))]
    return (left.ljust(width - len(right)) + right)[:width]


def fetch():
    """Rows from the tmux server, or None when there is no server."""
    try:
        out = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", FORMAT],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return order(parse(out.stdout))


def jump_command(pane, tty):
    cmd = ["tmux", "switch-client"]
    if tty:
        cmd += ["-c", tty]
    return cmd + ["-t", pane]


def mark_read_command(pane):
    # Same transition as switching into the session (see .tmux.conf); also the way
    # out for a row left at working/permission by Esc, which fires no hook.
    return ["tmux", "set", "-p", "-t", pane, "@claude_state", "idle"]


def mark_read(pane):
    out = subprocess.run(mark_read_command(pane), capture_output=True, text=True)
    return out.stderr.strip() if out.returncode != 0 else None


def jump(pane, tty):
    """Switch the client to pane; returns an error message or None."""
    out = subprocess.run(jump_command(pane, tty), capture_output=True, text=True)
    if out.returncode != 0:
        return out.stderr.strip() or f"switch-client exited {out.returncode}"
    return None


HEADER = 1  # lines above the first row


def run(screen):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    colors = {
        "permission": curses.color_pair(1) | curses.A_BOLD,
        "done": curses.color_pair(2) | curses.A_BOLD,
        "working": curses.A_DIM,
        "idle": curses.A_DIM,
    }
    # Every mouse event, not just button 1: ncurses discards an event outside the
    # mask and then waits for more input with no timeout, so a right-click used to
    # freeze the display until the next keypress.
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    curses.mouseinterval(0)
    # The refresh tick comes from select() below, so nothing ncurses does with input
    # can stall it; getch only drains what is already there.
    screen.nodelay(True)

    tty = os.environ.get("CLAUDE_SIDEBAR_TTY", "")
    selected = None  # pane id, so the selection survives reordering
    message = ""
    rows = []

    while True:
        fetched = fetch()
        rows = fetched or []
        panes = [r.pane for r in rows]
        if selected not in panes:
            selected = panes[0] if panes else None

        height, width = screen.getmaxyx()
        capacity = max(0, height - HEADER - 1)
        index = panes.index(selected) if selected else 0
        top = max(0, index - capacity + 1)
        visible = rows[top : top + capacity]

        screen.erase()
        screen.addnstr(0, 0, "claude" if fetched is not None else "no tmux server", width - 1, curses.A_BOLD)
        now = int(time.time())
        for i, row in enumerate(visible):
            attr = colors[row.state] | (curses.A_REVERSE if row.pane == selected else 0)
            screen.addnstr(HEADER + i, 0, line(row, now, width - 1), width - 1, attr)
        if message:
            screen.addnstr(height - 1, 0, message, width - 1, curses.color_pair(1))
        screen.refresh()

        if not select.select([sys.stdin], [], [], 1.0)[0]:
            continue
        while (key := screen.getch()) != -1:
            message = ""
            index = panes.index(selected) if selected else 0
            # Not Esc: a mouse report curses fails to decode arrives as a bare Esc.
            if key == ord("q"):
                return
            if key in (ord("j"), curses.KEY_DOWN) and selected:
                selected = panes[min(index + 1, len(panes) - 1)]
            elif key in (ord("k"), curses.KEY_UP) and selected:
                selected = panes[max(index - 1, 0)]
            elif key in (curses.KEY_ENTER, 10, 13) and selected:
                message = jump(selected, tty) or ""
            elif key == ord("r") and selected:
                message = mark_read(selected) or ""
            elif key == curses.KEY_MOUSE:
                try:
                    _, _, y, _, bstate = curses.getmouse()
                except curses.error:
                    continue
                slot = y - HEADER
                if not 0 <= slot < len(visible):
                    continue
                if bstate & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED):
                    selected = visible[slot].pane
                    message = jump(selected, tty) or ""
                elif bstate & (curses.BUTTON3_PRESSED | curses.BUTTON3_CLICKED):
                    message = mark_read(visible[slot].pane) or ""


def main():
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    curses.wrapper(run)


if __name__ == "__main__":
    main()
