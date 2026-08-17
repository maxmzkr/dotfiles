#!/usr/bin/env python3
"""Tests for the commit trailer hook.

The hook exists to fight a standing instruction in Claude Code's own system
prompt, so the tests lean hard on the vectors that instruction actually uses:
`-m` with the trailer inline, a quoted heredoc, and a message written to a file
first. A vector that slips through is a trailer in a real commit.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import commit_trailer_check as chk

HOOK = Path(__file__).parent / "commit_trailer_check.py"

TRAILER = "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
ROBOT = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"


class TestDetection(unittest.TestCase):
    def test_canonical_trailer(self):
        self.assertTrue(chk.has_trailer(f"Add a thing\n\n{TRAILER}\n"))

    def test_lowercase_spelling(self):
        self.assertTrue(chk.has_trailer("x\n\nco-authored-by: claude <noreply@anthropic.com>"))

    def test_bare_claude_name_without_email(self):
        self.assertTrue(chk.has_trailer("x\n\nCo-Authored-By: Claude"))

    def test_anthropic_email_without_the_word_claude(self):
        self.assertTrue(chk.has_trailer("x\n\nCo-authored-by: Assistant <noreply@anthropic.com>"))

    def test_robot_generated_line(self):
        self.assertTrue(chk.has_trailer(f"x\n\n{ROBOT}\n"))

    def test_indented_trailer_still_counts(self):
        self.assertTrue(chk.has_trailer("x\n\n   Co-Authored-By: Claude <a@b>"))

    def test_human_coauthor_is_left_alone(self):
        self.assertFalse(
            chk.has_trailer("Add a thing\n\nCo-authored-by: Max Mizikar <maxmzkr@gmail.com>")
        )

    def test_prose_mentioning_claude_is_not_a_trailer(self):
        self.assertFalse(chk.has_trailer("Document how Claude parses the config"))

    def test_coauthor_line_naming_a_human_named_claude_is_ambiguous_but_allowed(self):
        """A trailer is only caught when the value looks like the tool, not a person.

        `Claude Dupont <claude.dupont@corp.example>` is a colleague. The email
        domain is what separates them: the tool's is always anthropic.com.
        """
        self.assertFalse(
            chk.has_trailer("x\n\nCo-authored-by: Claude Dupont <claude.dupont@corp.example>")
        )


class TestCommitWriteDetection(unittest.TestCase):
    def test_plain_commit(self):
        self.assertTrue(chk.is_commit_write("git commit -m 'x'"))

    def test_commit_with_global_dir_option(self):
        self.assertTrue(chk.is_commit_write("git -C /tmp/repo commit -m 'x'"))

    def test_commit_with_config_override(self):
        self.assertTrue(chk.is_commit_write("git -c user.name=t commit -m 'x'"))

    def test_commit_after_a_chained_command(self):
        self.assertTrue(chk.is_commit_write("git add -A && git commit -m 'x'"))

    def test_merge_and_revert_and_cherry_pick(self):
        self.assertTrue(chk.is_commit_write("git merge -m 'x' topic"))
        self.assertTrue(chk.is_commit_write("git revert --no-edit HEAD"))
        self.assertTrue(chk.is_commit_write("git cherry-pick -x abc123"))

    def test_read_only_git_commands_are_not_commit_writes(self):
        """`git log --grep='Co-Authored-By: Claude'` is how you AUDIT for the
        trailer. Denying it would make the hook block its own diagnostics."""
        self.assertFalse(chk.is_commit_write("git log --grep='Co-Authored-By: Claude'"))
        self.assertFalse(chk.is_commit_write("git show HEAD"))
        self.assertFalse(chk.is_commit_write("git log --format=%B -1"))

    def test_non_git_command_mentioning_commit(self):
        self.assertFalse(chk.is_commit_write("echo 'commit this later'"))

    def test_grep_over_a_file_named_commit(self):
        self.assertFalse(chk.is_commit_write("rg 'Co-Authored-By' commit.txt"))


class TestAmendExemption(unittest.TestCase):
    """`--amend --no-edit` reuses a message that already exists. The four kept
    commits on this repo's main carry the trailer, and amending on top of one is
    preserving a message the user chose to keep, not adding a new one."""

    def test_amend_no_edit_is_exempt(self):
        self.assertTrue(chk.is_message_reuse("git commit --amend --no-edit"))

    def test_bare_amend_opens_an_editor_and_is_exempt(self):
        self.assertTrue(chk.is_message_reuse("git commit --amend"))

    def test_amend_with_a_new_message_is_not_exempt(self):
        self.assertFalse(chk.is_message_reuse("git commit --amend -m 'new text'"))

    def test_amend_with_a_message_file_is_not_exempt(self):
        self.assertFalse(chk.is_message_reuse("git commit --amend -F msg.txt"))

    def test_amend_with_a_trailer_flag_is_not_exempt(self):
        self.assertFalse(
            chk.is_message_reuse("git commit --amend --trailer 'Co-Authored-By: Claude'")
        )

    def test_ordinary_commit_is_not_message_reuse(self):
        self.assertFalse(chk.is_message_reuse("git commit -m 'x'"))


class TestMessageFileReading(unittest.TestCase):
    """Writing the message to a file and passing -F is a real vector: the trailer
    never appears in the command string, so scanning the command alone misses it."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.msg = Path(self.dir) / "msg.txt"
        self.msg.write_text(f"Add a thing\n\n{TRAILER}\n")

    def test_dash_f_file_is_read(self):
        text = chk.scan_text(f"git commit -F {self.msg}")
        self.assertIn("Co-Authored-By", text)

    def test_long_file_flag_is_read(self):
        text = chk.scan_text(f"git commit --file {self.msg}")
        self.assertIn("Co-Authored-By", text)

    def test_equals_form_is_read(self):
        text = chk.scan_text(f"git commit --file={self.msg}")
        self.assertIn("Co-Authored-By", text)

    def test_missing_file_does_not_raise(self):
        chk.scan_text("git commit -F /nonexistent/nope.txt")

    def test_command_text_is_always_included(self):
        text = chk.scan_text("git commit -m 'plain'")
        self.assertIn("plain", text)


class TestExtraction(unittest.TestCase):
    def test_inline_message(self):
        self.assertTrue(chk.violates("Bash", {"command": f"git commit -m '{TRAILER}'"}))

    def test_heredoc_message(self):
        cmd = (
            "git commit -m \"$(cat <<'EOF'\n"
            "Add a thing\n\n"
            f"{ROBOT}\n\n{TRAILER}\n"
            "EOF\n)\""
        )
        self.assertTrue(chk.violates("Bash", {"command": cmd}))

    def test_trailer_flag(self):
        self.assertTrue(chk.violates(
            "Bash", {"command": "git commit -m x --trailer 'Co-Authored-By: Claude'"}))

    def test_clean_commit_passes(self):
        self.assertFalse(chk.violates("Bash", {"command": "git commit -m 'Add a thing'"}))

    def test_human_coauthor_commit_passes(self):
        cmd = "git commit -m 'x\n\nCo-authored-by: Max Mizikar <maxmzkr@gmail.com>'"
        self.assertFalse(chk.violates("Bash", {"command": cmd}))

    def test_amend_no_edit_passes_even_if_head_has_the_trailer(self):
        self.assertFalse(chk.violates("Bash", {"command": "git commit --amend --no-edit"}))

    def test_audit_command_passes(self):
        cmd = "git log --grep='Co-Authored-By: Claude' --oneline"
        self.assertFalse(chk.violates("Bash", {"command": cmd}))

    def test_mcp_create_or_update_file(self):
        self.assertTrue(chk.violates(
            "mcp__claude_ai_GitHub_MCP__create_or_update_file",
            {"message": f"Add a thing\n\n{TRAILER}"}))

    def test_mcp_push_files(self):
        self.assertTrue(chk.violates(
            "mcp__claude_ai_GitHub_MCP__push_files", {"message": f"x\n\n{ROBOT}"}))

    def test_mcp_merge_pull_request_commit_message(self):
        self.assertTrue(chk.violates(
            "mcp__claude_ai_GitHub_MCP__merge_pull_request",
            {"commit_title": "Merge", "commit_message": f"x\n\n{TRAILER}"}))

    def test_mcp_clean_message_passes(self):
        self.assertFalse(chk.violates(
            "mcp__claude_ai_GitHub_MCP__push_files", {"message": "Add a thing"}))

    def test_unrelated_tool_passes(self):
        self.assertFalse(chk.violates("Read", {"file_path": "/tmp/x"}))

    def test_unrelated_bash_passes(self):
        self.assertFalse(chk.violates("Bash", {"command": "go test ./..."}))


class TestMalformedInput(unittest.TestCase):
    """The payload crosses a process boundary, so the type hints are advisory.
    Every one of these must be False rather than an exception: an exception in a
    PreToolUse hook matched on `Bash` breaks every command the user runs."""

    def test_non_string_tool_name(self):
        self.assertFalse(chk.violates(None, {"command": "git commit -m x"}))

    def test_non_dict_tool_input(self):
        self.assertFalse(chk.violates("Bash", "not a dict"))

    def test_non_string_command(self):
        self.assertFalse(chk.violates("Bash", {"command": 12345}))

    def test_missing_command(self):
        self.assertFalse(chk.violates("Bash", {}))

    def test_unbalanced_quotes_do_not_raise(self):
        self.assertFalse(chk.violates("Bash", {"command": "git commit -m 'unclosed"}))

    def test_unbalanced_quotes_with_trailer_still_caught(self):
        """shlex gives up on unbalanced quotes, but the raw-text scan does not."""
        self.assertTrue(
            chk.violates("Bash", {"command": f"git commit -m 'unclosed {TRAILER}"}))


class TestHookIO(unittest.TestCase):
    def _run(self, payload, env_extra=None):
        env = dict(os.environ)
        env.pop("COMMIT_TRAILER_CHECK", None)
        env.update(env_extra or {})
        return subprocess.run(
            ["python3", str(HOOK)], input=json.dumps(payload),
            capture_output=True, text=True, env=env,
        )

    def test_clean_commit_is_silent(self):
        proc = self._run({"tool_name": "Bash",
                          "tool_input": {"command": "git commit -m 'Add a thing'"}})
        self.assertEqual(0, proc.returncode)
        self.assertEqual("", proc.stdout.strip())

    def test_trailer_emits_deny_json(self):
        proc = self._run({"tool_name": "Bash",
                          "tool_input": {"command": f"git commit -m 'x\n\n{TRAILER}'"}})
        self.assertEqual(0, proc.returncode)
        hook = json.loads(proc.stdout)["hookSpecificOutput"]
        self.assertEqual("deny", hook["permissionDecision"])
        self.assertIn("Co-Authored-By", hook["permissionDecisionReason"])

    def test_deny_never_yields_on_repeat(self):
        """No soft tier. pr_body_check yields after one deny because its rules are
        taste; this one is an objective match against a standing system-prompt
        instruction that re-fires every time, so yielding would let it through."""
        payload = {"tool_name": "Bash",
                   "tool_input": {"command": f"git commit -m 'x\n\n{TRAILER}'"}}
        for _ in range(3):
            hook = json.loads(self._run(payload).stdout)["hookSpecificOutput"]
            self.assertEqual("deny", hook["permissionDecision"])

    def test_escape_hatch(self):
        proc = self._run(
            {"tool_name": "Bash",
             "tool_input": {"command": f"git commit -m 'x\n\n{TRAILER}'"}},
            env_extra={"COMMIT_TRAILER_CHECK": "off"})
        self.assertEqual("", proc.stdout.strip())

    def test_malformed_stdin_exits_clean(self):
        proc = subprocess.run(["python3", str(HOOK)], input="not json at all",
                              capture_output=True, text=True, env=dict(os.environ))
        self.assertEqual(0, proc.returncode)
        self.assertEqual("", proc.stdout.strip())

    def test_empty_stdin_exits_clean(self):
        proc = subprocess.run(["python3", str(HOOK)], input="",
                              capture_output=True, text=True, env=dict(os.environ))
        self.assertEqual(0, proc.returncode)
        self.assertEqual("", proc.stdout.strip())


if __name__ == "__main__":
    unittest.main()
