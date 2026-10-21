# Copilot agent to repo

An open-source converter that turns a Copilot Studio agent inventory into a Kortix project you can version: one `kortix.yaml`, one Markdown file per agent, one skill file per topic.

Kortix is the open-source AI Operating System this converter targets (`https://kortix.com`). A Kortix project keeps its agents in a git repository your team owns, so an agent's instructions, scope and grants are reviewable in a pull request instead of living only inside a Power Platform environment.

- The comparison that argues the switch: <https://opensourcecopilotalternative.com/kortix-vs-copilot>
- What a converted agent looks like once it runs, and where the canvas model stops: <https://opensourcecopilotalternative.com/copilot-studio-agent>
- MIT, see `LICENSE`

## The problem this solves

Microsoft's own documentation is explicit that a Copilot Studio agent is created *within a Power Platform solution*, and that solutions are how agents move between environments. That is a working deployment story inside Power Platform. It is not a version story: a topic's trigger phrases and messages are edited in a canvas, and the diff a reviewer sees is a solution export, not a text change.

The part of an agent that actually decides what it does — its instructions, its topics, the tools it may call — is text. This converter takes that text out of the canvas and writes it as files.

## What it does

Given a CSV or JSON inventory with one row per topic:

```csv
agent,topic,trigger_phrases,instructions,tools
support-triage,refund-request,"refund;money back;charged twice","Ask for the order id, check the refund window, then hand off to a human if the amount is over 200.","lookup_order,create_refund"
```

it writes:

```
project/
  kortix.yaml            # agents map, each pointing at its file
  agents/support-triage.md
  skills/refund-request.md
  README.md              # what to fill in by hand
```

The tool does not invent content. Every instruction line in the output is the instruction text you supplied; the mapping it applies is documented in `docs/mapping.md` and is deliberately small.

## Install and run

```bash
git clone https://github.com/ArtemShatokhin/copilot-agent-to-repo
cd copilot-agent-to-repo
python convert.py examples/inventory.csv --out /tmp/project
python convert.py examples/inventory.json --out /tmp/project --force
```

Standard library only, Python 3.11+. `--force` overwrites an existing output directory; without it the tool refuses and names what is already there.

## What the output is, and is not

It is a starting project: `kortix.yaml` valid against the starter's schema, one agent file per agent, one skill per topic, and a `README.md` listing the three things only a person can fill in — the connector credentials, the permission grants, and the answer to "which of these topics may act without approval".

It is not a migration. Trigger phrases do not transfer as trigger phrases: in Kortix an agent reads its instructions and picks a skill, so the phrases become examples inside the skill file, which is why they are kept verbatim and labelled. Anything the canvas held that is not text — a flow, a connector credential, an environment setting — is not in the output and the README says so by name.

## Fixtures

`examples/inventory.csv` and `examples/inventory.json` describe two agents with five topics between them, written to exercise the awkward cases: a phrase list with semicolons, an instruction containing a comma, and a topic with no tools. They are examples, not a recorded export of a real tenant.

## Contributing

A mapping change is a change to `docs/mapping.md` plus a row in the fixture that proves it. If a real export breaks the converter, open an issue with the row shape (not the customer's text) and the traceback.
