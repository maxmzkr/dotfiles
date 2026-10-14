import unittest

from sidebar import Row, age, jump_command, label, line, mark_read_command, order, parse


def row(state, since=0, pane="%1", session="s"):
    return Row(pane, session, state, since)


class ParseTest(unittest.TestCase):
    def test_keeps_only_panes_with_a_known_state(self):
        out = "\n".join(
            [
                "%1\tmaxmzkr-a\tdone\t100",
                "%2\tb\t\t",
                "%3\tc\tbogus\t5",
            ]
        )
        self.assertEqual(parse(out), [Row("%1", "maxmzkr-a", "done", 100)])

    def test_missing_since_parses_as_zero(self):
        self.assertEqual(parse("%1\ta\tidle\t")[0].since, 0)


class OrderTest(unittest.TestCase):
    def test_idle_then_permission_then_done_then_working_oldest_first(self):
        rows = [
            row("idle", 1, "%1"),
            row("working", 1, "%2"),
            row("done", 20, "%3"),
            row("permission", 5, "%4"),
            row("done", 10, "%5"),
        ]
        self.assertEqual([r.pane for r in order(rows)], ["%1", "%4", "%5", "%3", "%2"])


class FormatTest(unittest.TestCase):
    def test_label_strips_only_a_leading_prefix(self):
        self.assertEqual(label("maxmzkr-cert-backlog"), "cert-backlog")
        self.assertEqual(label("fix-maxmzkr-x"), "fix-maxmzkr-x")

    def test_age_picks_the_largest_whole_unit(self):
        self.assertEqual(
            [age(s) for s in (5, 60, 3599, 7200, 90000, -3)],
            ["5s", "1m", "59m", "2h", "1d", "0s"],
        )

    def test_line_puts_age_flush_right(self):
        r = row("permission", 1000, session="maxmzkr-cert-backlog")
        self.assertEqual(line(r, 1120, 20), "⚠ cert-backlog    2m")

    def test_line_cuts_the_name_before_the_age(self):
        r = row("done", 1000, session="a-very-long-session-name")
        self.assertEqual(line(r, 1045, 12), "✓ a-very 45s")

    def test_line_without_since_has_no_age(self):
        self.assertEqual(line(row("idle", 0, session="x"), 50, 6), "· x   ")


class JumpCommandTest(unittest.TestCase):
    def test_targets_the_given_client(self):
        self.assertEqual(
            jump_command("%7", "/dev/pts/3"),
            ["tmux", "switch-client", "-c", "/dev/pts/3", "-t", "%7"],
        )

    def test_without_a_tty_lets_tmux_pick_the_client(self):
        self.assertEqual(jump_command("%7", ""), ["tmux", "switch-client", "-t", "%7"])


class MarkReadCommandTest(unittest.TestCase):
    def test_sets_the_pane_idle(self):
        self.assertEqual(mark_read_command("%7"), ["tmux", "set", "-p", "-t", "%7", "@claude_state", "idle"])


if __name__ == "__main__":
    unittest.main()
