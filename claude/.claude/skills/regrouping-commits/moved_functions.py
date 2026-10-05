#!/usr/bin/env python3
"""Report functions a commit moved without changing.

A commit that reorders code it does not touch pads its own diff: the reviewer
reads the same body twice, once as a deletion and once as an addition. Run this
over each commit of a rewritten branch; anything it prints is diff the idea did
not need, unless the move IS the idea (extracting a file, regrouping a package).

    ./moved_functions.py <base>..HEAD          # every commit in the range
    ./moved_functions.py <sha>                 # one commit

Go and TypeScript/JavaScript out of the box; add a pattern for other languages.
Insertions do not count as moves -- position is compared against the longest
common subsequence of the two orders, not against the raw index.
"""
import difflib
import re
import subprocess
import sys

# The whole signature line is the name, so a Go receiver or a TS generic keeps
# two same-named methods apart.
DECL = re.compile(r'^(?:export\s+)?(?:async\s+)?(?:func|function|class|def)\b[^\n{:]*', re.M)


def blocks(rev, path):
    """{name: body}, [name...] for one file at one revision."""
    try:
        src = subprocess.run(['git', 'show', f'{rev}:{path}'],
                             capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        return {}, []
    bodies, order = {}, []
    for m in DECL.finditer(src):
        start = m.start()
        end = src.find('\n}\n', start)
        if end == -1:
            continue
        name = m.group(0).strip()
        bodies[name] = src[start:end + 3]
        order.append(name)
    return bodies, order


def reordered(before, after):
    """Names present in both whose relative order changed."""
    common_b = [n for n in before if n in set(after)]
    common_a = [n for n in after if n in set(before)]
    matcher = difflib.SequenceMatcher(a=common_b, b=common_a, autojunk=False)
    stable = {common_b[blk.a + i] for blk in matcher.get_matching_blocks() for i in range(blk.size)}
    return [n for n in common_b if n not in stable]


def report(sha, subject):
    files = subprocess.run(['git', 'show', '--name-only', '--format=', '-r', sha],
                           capture_output=True, text=True, check=True).stdout.split()
    lines, names = 0, []
    for path in files:
        if not path.endswith(('.go', '.ts', '.tsx', '.js', '.jsx', '.py')):
            continue
        old_bodies, old_order = blocks(sha + '~', path)
        new_bodies, new_order = blocks(sha, path)
        for name in reordered(old_order, new_order):
            if old_bodies[name] == new_bodies[name]:
                lines += new_bodies[name].count('\n')
                names.append(f'{path}:{name}')
    print(f'{lines:6d}  {sha} {subject}')
    for name in names:
        print(f'          {name}')
    return lines


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else 'origin/main..HEAD'
    fmt = ['git', 'log', '--format=%h %s', '--reverse']
    fmt += [target] if '..' in target else ['-1', target]
    total = 0
    for line in subprocess.run(fmt, capture_output=True, text=True, check=True).stdout.splitlines():
        sha, subject = line.split(' ', 1)
        total += report(sha, subject)
    print(f'\n{total} lines of moved-but-unchanged code')
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
