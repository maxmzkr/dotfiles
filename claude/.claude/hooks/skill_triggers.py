#!/usr/bin/env python3
"""Re-surface a skill whose trigger phrase appears in the prompt.

The skill catalog is injected once, at session start. It does not survive
compaction: every listing after a compact names only the skills already
invoked, so a long session ends up with no idea which skills exist. A trigger
phrase in a skill's own description is then unreachable -- the description is
not in context to be matched against.

This hook closes that gap from the outside. It reads the quoted phrases out of
each SKILL.md description -- the existing convention is to write triggers as
"hand hold", "watch CI" -- so no new metadata is needed and a new skill is
covered the moment it is written.

Registered on UserPromptSubmit. It must never fail: a UserPromptSubmit hook
that errors rejects the prompt.
"""

import json
import os
import re
import sys

SKILLS_DIR = os.path.expanduser("~/.claude/skills")

# Two words or more. A single quoted word ("review", "plan") matches far too
# much ordinary conversation to be worth surfacing.
PHRASE = re.compile(r'"([^"]{4,60})"')
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def skills():
    """Yield (name, description) for every skill on disk."""
    try:
        entries = sorted(os.listdir(SKILLS_DIR))
    except OSError:
        return
    for entry in entries:
        path = os.path.join(SKILLS_DIR, entry, "SKILL.md")
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(4096)
        except OSError:
            continue
        m = FRONTMATTER.match(head)
        if not m:
            continue
        block = m.group(1)
        name = entry
        desc = ""
        for field, value in re.findall(r"^(\w+):[ \t]*(.*)$", block, re.M):
            if field == "name":
                name = value.strip()
            elif field == "description":
                desc = value.strip()
        if desc:
            yield name, desc


def triggers(description):
    """The quoted multi-word phrases a description offers as triggers.

    Descriptions quote two different things: the phrases the user might say,
    and ordinary prose ("from 'just pushed' to 'reviewers pinged'"). Where the
    description says "Triggers on", only what follows counts -- otherwise the
    prose half of that sentence fires the skill on any mention of a push.
    """
    marker = re.search(r"[Tt]rigger", description)
    scope = description[marker.start():] if marker else description
    out = []
    for phrase in PHRASE.findall(scope):
        phrase = phrase.strip()
        if " " in phrase:
            out.append(phrase)
    return out


def matches(prompt):
    low = prompt.lower()
    hits = []
    for name, desc in skills():
        for phrase in triggers(desc):
            # Word-boundary so "plan" inside "planning" does not count.
            if re.search(r"\b" + re.escape(phrase.lower()) + r"\b", low):
                hits.append((name, phrase, desc))
                break
    return hits


def format_block(hits):
    lines = [
        "This prompt contains a phrase that a skill names as its trigger. "
        "The skill catalog is not re-injected after a compaction, so this is "
        "how you find out the skill exists. Invoke it with the Skill tool "
        "before acting -- including when the prompt also spells out the "
        "individual steps, since a spelled-out request is usually the tail of "
        "the skill's process with its prerequisites left implicit.",
        "",
    ]
    for name, phrase, desc in hits:
        lines.append(f'- {name} — matched "{phrase}"')
        lines.append(f"  {desc}")
    return "\n".join(lines)


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        return
    data = json.loads(raw)
    prompt = data.get("prompt") or ""
    if not prompt.strip():
        return
    hits = matches(prompt)
    if not hits:
        return
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": data.get("hook_event_name", "UserPromptSubmit"),
                "additionalContext": format_block(hits),
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # A hook that breaks the prompt is worse than a hook that says nothing.
        pass
    sys.exit(0)
