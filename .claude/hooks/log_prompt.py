"""Claude Code UserPromptSubmit hook: append each prompt to docs/PROMPTS.md.

Reads the hook payload (JSON) from stdin. The log path is resolved from this
script's location, so it works whatever directory the Claude session runs in.
Never blocks the prompt: any error is swallowed and the hook exits 0.
"""

import contextlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = REPO_ROOT / "docs" / "PROMPTS.md"

HEADER = (
    "# Prompt Log\n\n"
    "Every prompt sent to Claude Code for this project, oldest first.\n"
    "Appended automatically by `.claude/hooks/log_prompt.py` (UserPromptSubmit hook).\n"
)

# Context the IDE attaches to a prompt; not typed by the user.
IDE_TAGS = re.compile(r"<(ide_opened_file|ide_selection)>.*?</\1>\s*", re.S)


def current_branch() -> str:
    try:
        out = subprocess.run(  # noqa: S603 - fixed arguments, no user input
            ["git", "-C", str(REPO_ROOT), "branch", "--show-current"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or "detached"
    except Exception:
        return "unknown"


def main() -> None:
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    payload = json.loads(raw) if raw.strip() else {}
    prompt = IDE_TAGS.sub("", payload.get("prompt") or "").strip()
    if not prompt:
        return

    existing = LOG_FILE.read_text(encoding="utf-8") if LOG_FILE.exists() else ""
    if not existing:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing = HEADER

    fence = "````" if "```" in prompt else "```"
    # Skip if this exact prompt is already the last entry (hook registered twice).
    if existing.rstrip().endswith(f"{fence}text\n{prompt}\n{fence}"):
        return

    count = existing.count("\n## Prompt ") + 1
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n## Prompt {count}\n\n"
        f"- **Time:** {stamp}\n"
        f"- **Branch:** `{current_branch()}`\n\n"
        f"{fence}text\n{prompt}\n{fence}\n"
    )
    LOG_FILE.write_text(existing + entry, encoding="utf-8")


if __name__ == "__main__":
    # A logging failure must never block the prompt.
    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
