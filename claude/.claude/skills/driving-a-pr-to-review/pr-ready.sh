#!/bin/sh
# Stages 1-3 as one gate: CI green, out of draft, reviewers verified.
#
# Usage: pr-ready.sh <pr> [login[,login...]]
#
# Run this INSTEAD of `gh pr edit --add-reviewer` and `gh pr ready`. It refuses at the
# first unmet condition and exits nonzero, so the Slack ask in stage 4 cannot go out
# ahead of the thing it is asking people to look at. With no logins it only reports.
#
# It exists because the failure is not forgetting the stages -- it is being handed the
# last two ("request sam, post this in #channel") and doing exactly those.
set -e

pr=$1
logins=$2
[ -n "$pr" ] || { echo "usage: pr-ready.sh <pr> [login,...]" >&2; exit 2; }

checks=$(gh pr checks "$pr" --json name,bucket,link 2>/dev/null || true)
if [ -z "$checks" ]; then
    # Empty is an API hiccup or a PR with no checks yet -- never success.
    echo "gate:    BLOCKED -- no check data for #$pr (API hiccup, or checks not registered yet)"
    exit 1
fi

echo "checks:  $(printf '%s' "$checks" | jq -r '[group_by(.bucket)[] | "\(.[0].bucket)=\(length)"] | join(" ")')"

pending=$(printf '%s' "$checks" | jq -r '[.[] | select(.bucket=="pending")] | length')
bad=$(printf '%s' "$checks" | jq -r '.[] | select(.bucket=="fail" or .bucket=="cancel") | "  \(.bucket)\t\(.name)\t\(.link)"')

if [ "$pending" -ne 0 ]; then
    printf '%s' "$checks" | jq -r '.[] | select(.bucket=="pending") | "  pending\t\(.name)"'
    echo "gate:    BLOCKED -- $pending check(s) still running; watch them, do not ask for review yet"
    exit 1
fi
if [ -n "$bad" ]; then
    echo "$bad"
    echo "gate:    BLOCKED -- read the log and classify before rerunning (SKILL.md stage 2)"
    exit 1
fi

# A draft PR cannot be reviewed, so this is the moment it flips -- after green.
if [ "$(gh pr view "$pr" --json isDraft -q .isDraft)" = "true" ]; then
    if [ -z "$logins" ]; then
        echo "gate:    BLOCKED -- CI is green but #$pr is still a draft; rerun with the reviewer logins"
        exit 1
    fi
    gh pr ready "$pr"
    echo "draft:   cleared"
else
    echo "draft:   already clear"
fi

if [ -n "$logins" ]; then
    gh pr edit "$pr" --add-reviewer "$logins" >/dev/null
fi

# gh exits 0 while silently dropping a login it does not recognize.
have=$(gh pr view "$pr" --json reviewRequests --jq '[.reviewRequests[].login] | join(",")')
echo "reviewers: ${have:-(none)}"
missing=
for want in $(printf '%s' "$logins" | tr ',' ' '); do
    case ",$have," in
      *",$want,"*) ;;
      *) missing="$missing $want" ;;
    esac
done
if [ -n "$missing" ]; then
    echo "gate:    BLOCKED -- gh dropped:$missing (wrong handle; fix references/directory.json, do not retry the same string)"
    exit 1
fi
if [ -z "$have" ]; then
    echo "gate:    BLOCKED -- no reviewers on #$pr; nothing to announce in Slack"
    exit 1
fi

echo "gate:    READY -- stage 4 (Slack) may go out now"
