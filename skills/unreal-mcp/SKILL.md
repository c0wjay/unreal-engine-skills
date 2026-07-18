---
name: unreal-mcp
description: "Operate or inspect a live Unreal Editor through Unreal MCP. Use for actor, asset, Blueprint, UMG, material, Niagara, GAS, gameplay-tag, automation, editor-log, PIE-state, and live-editor requests; for reading Blueprint graphs or planning BP-to-C++ ports; and when UE signals such as `.uproject`, `BP_`, `WBP_`, `UCLASS`, Content Browser, or World Outliner make the Unreal context clear. Skip pure conceptual Unreal questions, authoring toolset code (use create-toolset), authoring Unreal Agent Skills (use unreal-skill), and unrelated engines."
---

# Unreal MCP

Use the live editor as the source of truth for asset and runtime-editor state. Read the nearest project guidance before
calling tools; repository policy overrides this generic workflow.

## Establish the boundary

1. Classify the request as read-only inspection, live mutation, or a user-executed editor handoff.
2. Check local rules for builds, source control, Engine edits, Blueprint mutation, and required verification.
3. If the editor or MCP server is unavailable, say so. Do not infer live asset state from stale text exports.

Apply these hard boundaries:

- Do not create, edit, compile, save, rename, or delete Blueprint/Widget/Anim Blueprint assets. Use Unreal MCP only to
  inspect them. Give the USER an exact ordered Korean editor checklist, then verify the result read-only after they
  perform it.
- Do not run or request builds. Use available static diagnostics and leave compilation to the USER.
- Never modify `Engine/`. Extend through project or plugin code.
- Use the `perforce-mcp` skill before changing tracked source or project files.

## Discover and call tools

Support both host exposure styles:

- If the server exposes `list_toolsets`, `describe_toolset`, and `call_tool`, describe the relevant toolset and dispatch
  through `call_tool`. Skip `list_toolsets` when the needed domain is already clear.
- If the host exposes individual flattened MCP tools, select the smallest relevant tool directly and follow its schema.
  Do not assume another client uses the same flattened name.

Prefer narrow queries. Serialize Unreal MCP calls: they run against shared editor/game-thread state, and parallel calls
can collide even when they appear independent. Check every returned status before continuing.

## Inspect or mutate safely

- Check PIE and compilation state before editor-only operations.
- Create a recovery point before permitted bulk mutation and save only after confirming success.
- Treat Python/programmatic editor execution as privileged bulk access. Keep its scope explicit and never use it to
  bypass project mutation rules.
- After a permitted mutation, re-read the affected asset or editor state rather than trusting the write response alone.

## Read Blueprint graphs and port to C++

For Blueprint audits, override detection, graph reconstruction, or BP-to-C++ work, read
`references/blueprint-graph-reading.md` before inspecting the graph. Its connected-pin workflow is mandatory because
the graph DSL is lossy around dead-end exec pins, branch polarity, and Boolean Select nodes.

## Load project Agent Skills

When the project is unfamiliar, query `AgentSkillToolset` for registered Unreal Agent Skills. Load a relevant skill's
full instructions before acting. Unreal Agent Skills are editor-registered knowledge objects; they are distinct from
this Claude/Codex harness skill.

## References

- `references/blueprint-graph-reading.md`: reliable Blueprint audit and BP-to-C++ reconstruction.
- `references/setup.md`: first-time server/client configuration, including the Project-specific plugin and port policy.
- `references/operations.md`: console commands, tool exposure modes, and recovery steps.

## Companion skills

- Use `create-toolset` to add or redesign AI-callable Unreal toolsets.
- Use `unreal-skill` to create or revise Unreal Agent Skills registered inside the editor.
