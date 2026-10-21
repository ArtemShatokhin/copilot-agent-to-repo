#!/usr/bin/env python3
"""Convert a Copilot Studio agent inventory (CSV or JSON) into a Kortix project.

    python convert.py examples/inventory.csv --out /tmp/project
    python convert.py examples/inventory.json --out /tmp/project --force

Row shape (CSV header or JSON object keys):

    agent            agent name, used as the file name and the agents-map key
    topic            one topic / skill per row
    trigger_phrases  semicolon-separated buyer phrases, kept verbatim
    instructions     what the topic must do, kept verbatim
    tools            comma-separated tool names the topic may call

The converter writes text it was given. It does not summarise, rewrite or
invent instructions, and it refuses a row with an empty instructions field
instead of filling one in.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ("agent", "topic", "trigger_phrases", "instructions", "tools")
SLUG = re.compile(r"[^a-z0-9]+")

README_TEMPLATE = """# {project}

A Kortix project generated from a Copilot Studio agent inventory on {date}.

## Fill in by hand

1. **Connectors and credentials.** `kortix.yaml` lists the tools each agent may
   call by name only. Declare the connectors and their secrets before running an
   agent; a name with no connector behind it fails at the first call, loudly.
2. **Permission grants.** Every agent file starts from deny-by-default. Grant
   the resources each agent may read or write, and decide which of these topics
   may act without a person approving the result.
3. **Approval points.** The instructions say what a topic does, not who signs
   off. Add the approval step to any topic that moves money, changes access or
   writes to a system of record.

## What did not come across

A Copilot Studio solution export carries component definitions; this project
carries instructions, skills and grants as text. Anything that was not text —
a flow, a connector's authentication, an environment variable value, the
analytics behind a topic's usage — is not in these files. Rebuild those, and
keep this directory in git so the next change is a diff.

## Run it

    kortix run {first_agent}

Generated from {source}.
"""


def slug(value: str) -> str:
    return SLUG.sub("-", value.strip().lower()).strip("-") or "agent"


def load(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = raw["agents"] if isinstance(raw, dict) else raw
    else:
        with path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    rows = [{k: (r.get(k) or "").strip() for k in FIELDS} for r in rows]
    bad = [i + 2 for i, r in enumerate(rows) if not r["instructions"]]
    if bad:
        raise SystemExit(f"row(s) with no instructions: {bad} — refusing to invent one")
    missing = [r for r in rows if not r["agent"] or not r["topic"]]
    if missing:
        raise SystemExit("every row needs an agent and a topic")
    return rows


def split_list(value: str, sep: str) -> list[str]:
    return [p.strip() for p in value.split(sep) if p.strip()]


def agent_file(name: str, topics: list[dict]) -> str:
    lines = [
        f"# {name}",
        "",
        "You are the {name} agent. You answer questions and take actions only "
        "through the skills listed below, and only inside the permissions granted "
        "to you in `kortix.yaml`.".replace("{name}", name),
        "",
        "Work in this order:",
        "",
        "1. Read the request and pick the skill that matches it.",
        "2. Follow that skill's instructions exactly; do not improvise a step the "
        "skill does not list.",
        "3. If no skill matches, say what you can do and stop. Do not guess a "
        "tool name.",
        "4. If a step needs approval that has not been given, ask for it and wait.",
        "",
        "## Skills",
        "",
    ]
    for t in topics:
        lines.append(f"- `{slug(t['topic'])}` — {t['instructions'].split('.')[0]}.")
    lines += [
        "",
        "## Boundaries",
        "",
        "- Never call a tool that is not declared for the skill you are running.",
        "- Never repeat a credential, a token or a customer's personal data into a "
        "summary.",
        "- When a request is ambiguous, ask one question rather than acting twice.",
        "",
    ]
    return "\n".join(lines)


def skill_file(topic: dict) -> str:
    phrases = split_list(topic["trigger_phrases"], ";")
    tools = split_list(topic["tools"], ",")
    lines = [f"# {topic['topic']}", "", "## Instructions", "", topic["instructions"], ""]
    if phrases:
        lines += [
            "## Phrases a person has used for this",
            "",
            "Copied verbatim from the Copilot Studio topic. They are examples of the "
            "request, not a keyword list: match the intent, not the string.",
            "",
        ]
        lines += [f"- {p}" for p in phrases]
        lines.append("")
    if tools:
        lines += ["## Tools", ""] + [f"- `{t}`" for t in tools] + [
            "",
            "Every tool above must be declared as a connector in `kortix.yaml` before "
            "this skill runs.",
            "",
        ]
    else:
        lines += ["## Tools", "", "None. This skill answers from what it is told.", ""]
    return "\n".join(lines)


def yaml_block(agents: dict[str, list[dict]]) -> str:
    out = [
        "kortix_version: 2",
        "default_agent: " + slug(next(iter(agents))),
        "agents:",
    ]
    for name, topics in agents.items():
        tools = sorted({t for topic in topics for t in split_list(topic["tools"], ",")})
        out += [
            f"  {slug(name)}:",
            f"    file: agents/{slug(name)}.md",
            "    connectors:" + (" [" + ", ".join(tools) + "]" if tools else " []"),
            "    secrets: all",
            "    kortix_permissions: []  # grant by resource; deny by default",
            "    skills:",
        ]
        out += [f"      - skills/{slug(t['topic'])}.md" for t in topics]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inventory", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--project", default=None, help="project name; defaults to --out's name")
    ap.add_argument("--force", action="store_true", help="overwrite a non-empty --out")
    args = ap.parse_args()

    rows = load(args.inventory)
    out: Path = args.out
    if out.exists() and any(out.iterdir()):
        if not args.force:
            have = ", ".join(sorted(p.name for p in out.iterdir())[:6])
            raise SystemExit(f"{out} is not empty ({have}) — pass --force to overwrite")
        shutil.rmtree(out)

    agents: dict[str, list[dict]] = {}
    for row in rows:
        agents.setdefault(row["agent"], []).append(row)

    (out / "agents").mkdir(parents=True, exist_ok=True)
    (out / "skills").mkdir(parents=True, exist_ok=True)
    for name, topics in agents.items():
        (out / "agents" / f"{slug(name)}.md").write_text(agent_file(name, topics), encoding="utf-8")
        for topic in topics:
            (out / "skills" / f"{slug(topic['topic'])}.md").write_text(skill_file(topic), encoding="utf-8")
    (out / "kortix.yaml").write_text(yaml_block(agents), encoding="utf-8")
    (out / "README.md").write_text(
        README_TEMPLATE.format(project=args.project or out.name,
                               date=datetime.now(timezone.utc).strftime("%Y-%m-%d"), source=args.inventory.name,
                               first_agent=slug(next(iter(agents)))),
        encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "agents": len(agents),
        "skills": sum(len(t) for t in agents.values()),
        "files": sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
