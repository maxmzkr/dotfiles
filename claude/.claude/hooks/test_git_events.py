#!/usr/bin/env python3
"""Tests for the git activity hook, driving real git repos in temp dirs.

Every test builds an actual repository and runs actual git commands. The whole
point of the hook is that it reads what git wrote to the reflog, so faking the
reflog would test nothing.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import git_events as ge

HOOK = Path(__file__).parent / "git_events.py"


def git(repo, *args, **kw):
    """Run git in `repo` with a hermetic config, returning stdout."""
    env = dict(os.environ)
    env.update(
        GIT_CONFIG_GLOBAL="/dev/null",
        GIT_CONFIG_SYSTEM="/dev/null",
        GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@example.com",
        GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@example.com",
        GIT_AUTHOR_DATE="2026-01-01T00:00:00Z",
        GIT_COMMITTER_DATE="2026-01-01T00:00:00Z",
    )
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        env=env, capture_output=True, text=True, check=True, **kw
    ).stdout


def commit(repo, name, body=None):
    (Path(repo) / name).write_text(body or name)
    git(repo, "add", name)
    git(repo, "commit", "-m", name)


class RepoCase(unittest.TestCase):
    """Base: a temp dir plus an initialized repo with one commit."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        commit(self.repo, "base")

    def collect(self, marker=None):
        """Read events since `marker`; returns (lines, new_marker)."""
        return ge.collect(str(self.repo), marker)

    def baseline(self):
        _, marker = self.collect(None)
        return marker

    def since_baseline(self, *do):
        """Baseline, run each callable, then report what the hook sees."""
        marker = self.baseline()
        for fn in do:
            fn()
        lines, _ = self.collect(marker)
        return lines


class FirstRun(RepoCase):
    def test_first_run_reports_nothing(self):
        lines, _ = self.collect(None)
        self.assertEqual(lines, [])

    def test_first_run_marker_records_current_head_and_branch(self):
        _, marker = self.collect(None)
        head = git(self.repo, "rev-parse", "HEAD").strip()
        self.assertEqual(marker["head"], head)
        self.assertEqual(marker["branch"], "main")

    def test_quiet_repo_reports_nothing_on_second_run(self):
        self.assertEqual(self.since_baseline(), [])


class Commits(RepoCase):
    def test_commit_is_reported_with_its_subject(self):
        lines = self.since_baseline(lambda: commit(self.repo, "feature-a"))
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("commit", lines[0])
        self.assertIn("feature-a", lines[0])

    def test_consecutive_commits_collapse_to_one_line(self):
        lines = self.since_baseline(
            lambda: commit(self.repo, "one"),
            lambda: commit(self.repo, "two"),
            lambda: commit(self.repo, "three"),
        )
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("3 steps", lines[0])
        self.assertIn("three", lines[0], "newest subject should survive the collapse")

    def test_amend_keeps_its_parenthetical(self):
        lines = self.since_baseline(
            lambda: git(self.repo, "commit", "--amend", "-m", "reworded")
        )
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("amend", lines[0])

    def test_reported_shas_bracket_the_change(self):
        before = git(self.repo, "rev-parse", "HEAD").strip()
        lines = self.since_baseline(lambda: commit(self.repo, "feature-a"))
        after = git(self.repo, "rev-parse", "HEAD").strip()
        self.assertIn(before[:7], lines[0])
        self.assertIn(after[:7], lines[0])


class Checkouts(RepoCase):
    def test_checkout_reports_branch_names_not_shas(self):
        git(self.repo, "branch", "feature")
        lines = self.since_baseline(lambda: git(self.repo, "checkout", "feature"))
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("checkout", lines[0])
        self.assertIn("main -> feature", lines[0])

    def test_revisiting_a_sha_does_not_corrupt_an_earlier_before_sha(self):
        """Checkouts revisit shas already seen, so a sha is not a unique key.

        Here `main`'s tip appears twice in the reflog: once as the commit that
        created it, and again as the destination of the final checkout. The
        commit's "before" must stay `base`, not borrow the checkout's.
        """
        git(self.repo, "branch", "feature")
        base = git(self.repo, "rev-parse", "HEAD").strip()
        marker = self.baseline()
        commit(self.repo, "on-main")
        tip = git(self.repo, "rev-parse", "HEAD").strip()
        git(self.repo, "checkout", "feature")
        commit(self.repo, "on-feature")
        git(self.repo, "checkout", "main")

        lines, _ = self.collect(marker)
        first = lines[0]
        self.assertIn("on-main", first, lines)
        self.assertEqual(first, f'commit: {base[:7]} -> {tip[:7]} "on-main"', lines)

    def test_branch_change_updates_marker_branch(self):
        git(self.repo, "branch", "feature")
        marker = self.baseline()
        git(self.repo, "checkout", "feature")
        _, marker = self.collect(marker)
        self.assertEqual(marker["branch"], "feature")


class Rebases(RepoCase):
    def setUp(self):
        super().setUp()
        git(self.repo, "checkout", "-b", "feature")
        commit(self.repo, "f1")
        commit(self.repo, "f2")
        git(self.repo, "checkout", "main")
        commit(self.repo, "m1")
        git(self.repo, "checkout", "feature")

    def test_rebase_collapses_to_a_single_line(self):
        lines = self.since_baseline(
            lambda: git(self.repo, "rebase", "main")
        )
        rebase_lines = [line for line in lines if line.startswith("rebase")]
        self.assertEqual(len(rebase_lines), 1, lines)

    def test_rebase_line_omits_internal_bookkeeping_text(self):
        lines = self.since_baseline(lambda: git(self.repo, "rebase", "main"))
        joined = " ".join(lines)
        self.assertNotIn("returning to", joined)
        self.assertNotIn("refs/heads", joined)


class CherryPicks(RepoCase):
    def test_cherry_pick_is_reported_with_its_subject(self):
        commit(self.repo, "wanted")
        pick = git(self.repo, "rev-parse", "HEAD").strip()
        git(self.repo, "reset", "--hard", "HEAD~1")
        lines = self.since_baseline(
            lambda: git(self.repo, "cherry-pick", pick)
        )
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("cherry-pick", lines[0])
        self.assertIn("wanted", lines[0])


class Remotes(RepoCase):
    """A bare remote next door, so push and pull are the real commands."""

    def setUp(self):
        super().setUp()
        self.bare = self.tmp / "bare.git"
        git(self.tmp, "init", "--bare", "-b", "main", str(self.bare))
        git(self.repo, "remote", "add", "origin", str(self.bare))
        git(self.repo, "push", "-u", "origin", "main")

    def test_push_is_reported_for_the_remote_tracking_ref(self):
        commit(self.repo, "to-push")
        lines = self.since_baseline(
            lambda: git(self.repo, "push", "origin", "main")
        )
        pushes = [line for line in lines if "origin/main" in line]
        self.assertEqual(len(pushes), 1, lines)
        self.assertIn("push", pushes[0])

    def test_pull_is_reported(self):
        other = self.tmp / "other"
        git(self.tmp, "clone", str(self.bare), str(other))
        commit(other, "from-elsewhere")
        git(other, "push", "origin", "main")
        lines = self.since_baseline(
            lambda: git(self.repo, "pull", "origin", "main")
        )
        self.assertTrue(
            any("pull" in line or "merge" in line for line in lines),
            lines,
        )

    def test_untouched_remote_ref_is_silent(self):
        commit(self.repo, "local-only")
        lines = self.since_baseline(lambda: commit(self.repo, "still-local"))
        self.assertFalse([line for line in lines if "origin/" in line], lines)


class LostAnchor(RepoCase):
    def test_expired_reflog_reports_a_rewrite_instead_of_replaying_history(self):
        marker = self.baseline()
        commit(self.repo, "later")
        git(self.repo, "reflog", "expire", "--expire=all", "--all")
        lines, _ = self.collect(marker)
        self.assertTrue(any("rewritten" in line for line in lines), lines)


class NonRepos(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_plain_directory_yields_no_events_and_no_marker(self):
        lines, marker = ge.collect(str(self.tmp), None)
        self.assertEqual(lines, [])
        self.assertIsNone(marker)

    def test_missing_directory_yields_no_events_and_no_marker(self):
        lines, marker = ge.collect(str(self.tmp / "nope"), None)
        self.assertEqual(lines, [])
        self.assertIsNone(marker)


class MarkerFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_sessions_get_separate_markers(self):
        a = ge.marker_path(self.tmp, "session-a", "/home/max/dotfiles")
        b = ge.marker_path(self.tmp, "session-b", "/home/max/dotfiles")
        self.assertNotEqual(a, b)

    def test_repos_get_separate_markers(self):
        a = ge.marker_path(self.tmp, "session-a", "/home/max/dotfiles")
        b = ge.marker_path(self.tmp, "session-a", "/home/max/other")
        self.assertNotEqual(a, b)

    def test_marker_round_trips(self):
        path = ge.marker_path(self.tmp, "s", "/repo")
        ge.save_marker(path, {"head": "abc", "branch": "main"})
        self.assertEqual(ge.load_marker(path)["head"], "abc")

    def test_absent_marker_loads_as_none(self):
        self.assertIsNone(ge.load_marker(self.tmp / "not-there.json"))

    def test_corrupt_marker_loads_as_none(self):
        path = self.tmp / "bad.json"
        path.write_text("{not json")
        self.assertIsNone(ge.load_marker(path))


class Rendering(unittest.TestCase):
    def test_block_names_the_repo_and_branch(self):
        out = ge.format_block(
            "/home/max/dotfiles",
            ["commit: aaaaaaa -> bbbbbbb \"x\""],
            {"branch": "main", "head": "b" * 40},
        )
        self.assertIn('repo="/home/max/dotfiles"', out)
        self.assertIn('branch="main"', out)
        self.assertIn("commit:", out)

    def test_no_lines_renders_empty(self):
        self.assertEqual(ge.format_block("/r", [], {"branch": "main"}), "")


class EndToEnd(RepoCase):
    """Drive git_events.py the way Claude Code does: JSON on stdin."""

    def run_hook(self, event="UserPromptSubmit", session="sess-1"):
        payload = json.dumps(
            {"session_id": session, "cwd": str(self.repo), "hook_event_name": event}
        )
        proc = subprocess.run(
            [sys.executable, "-S", str(HOOK)],
            input=payload, capture_output=True, text=True,
            env={**os.environ, "XDG_CACHE_HOME": str(self.tmp / "cache")},
        )
        return proc

    def test_first_invocation_is_silent_and_succeeds(self):
        proc = self.run_hook()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_second_invocation_reports_the_commit_as_hook_json(self):
        self.run_hook()
        commit(self.repo, "seen-by-hook")
        proc = self.run_hook()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        out = payload["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "UserPromptSubmit")
        self.assertIn("seen-by-hook", out["additionalContext"])

    def test_event_name_is_echoed_back(self):
        self.run_hook(event="SessionStart")
        commit(self.repo, "x")
        proc = self.run_hook(event="SessionStart")
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["hookSpecificOutput"]["hookEventName"], "SessionStart"
        )

    def test_separate_sessions_each_get_their_own_baseline(self):
        self.run_hook(session="a")
        commit(self.repo, "only-a-saw-the-baseline")
        self.assertIn("only-a-saw-the-baseline", self.run_hook(session="a").stdout)
        self.assertEqual(self.run_hook(session="b").stdout.strip(), "")

    def test_garbage_stdin_exits_clean_and_silent(self):
        proc = subprocess.run(
            [sys.executable, "-S", str(HOOK)],
            input="not json", capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_non_repo_cwd_exits_clean_and_silent(self):
        payload = json.dumps(
            {"session_id": "s", "cwd": str(self.tmp), "hook_event_name": "UserPromptSubmit"}
        )
        proc = subprocess.run(
            [sys.executable, "-S", str(HOOK)],
            input=payload, capture_output=True, text=True,
            env={**os.environ, "XDG_CACHE_HOME": str(self.tmp / "cache")},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
