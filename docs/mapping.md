# Mapping: Copilot Studio inventory to a Kortix project

The converter applies one small, documented mapping. Everything else is copied
verbatim, and the places where the inventory cannot be copied are listed at the
end so the person finishing the project knows what to rebuild.

This mapping belongs to an open-source tool; change it here before changing the
code, so a reader can see what a row will become before running anything.

## Rows to files

| Inventory | Output | Rule |
| --- | --- | --- |
| `agent` | `agents/<slug>.md`, key in `agents:` of `kortix.yaml` | slugified; grouping key, never rewritten |
| `topic` | `skills/<slug>.md`, entry in the agent's `skills:` list | one topic, one skill file |
| `trigger_phrases` (semicolon-separated) | `## Phrases a person has used for this` | verbatim, one bullet each |
| `instructions` | `## Instructions` | verbatim, never summarised |
| `tools` (comma-separated) | `## Tools` plus the agent's `connectors:` list | names only; declarations are the human's job |

## Why skills, not topics

A Copilot Studio topic is a routing decision made by the canvas: a trigger
phrase enters, a topic runs, the topic's steps execute in order. A Kortix skill
is a file an agent reads and follows. The instructions transfer; the routing
does not. That is why the phrases are kept as examples under a heading that
says so, and why the agent file tells the agent to pick a skill and stop when
none matches, instead of guessing.

## Deny by default

Every generated agent gets `kortix_permissions: []` with a comment saying
grants are by resource. A converter that filled in permissions from a topic's
tools would ship an agent with more access than its author intended. The
generated README names the three decisions a person has to make: connectors and
their secrets, grants, and which skills may act without approval.

## What cannot come across

- **Flows.** A Power Automate flow behind a topic is a graph; there is no text
  form of it in an inventory row. Rebuild it as a skill step that calls a tool.
- **Connector authentication.** The inventory names a tool; the credential lives
  in the environment. Declare the connector and its secret in the new project.
- **Environment settings and analytics.** Usage, satisfaction and topic
  analytics stay in the source tenant and are not carried by any export.
- **The unmanaged layer.** Solution layering has no equivalent; the git history
  replaces it, which is the point of doing this at all.

## Fixture coverage

`examples/inventory.csv` exercises a semicolon phrase list, a comma inside an
instruction, and a topic with no tools. `examples/inventory.json` is the same
data in the other input shape. Both must produce byte-identical output apart
from the project name; that equality is the regression test.
