---
name: unreal-pcg
description: "Set up, validate, debug, profile or hand-edit Unreal PCG (Procedural Content Generation) graphs and their generated content, by following the PCG plugin's own skills for the project's engine version. Use for PCG runtime generation on landscape or mesh terrain, PCG performance, inspecting PCG node data, low-end-device PCG settings, or before editing any actor a PCG graph generated."
---

# Unreal PCG (engine plugin skill redirector)

The guidance ships with the engine's PCG plugin (UE 5.9 and later) and changes with each engine version, so this file
carries no copy of it.

1. Find the engine root from the project: `python -I "<this skill's base directory>/../../scripts/find_engine_root.py"
   "<project .uproject>"`. It prints the folder that holds `Engine/`.
2. Read `<root>/Engine/Plugins/PCG/Skills/SKILL.md` in full; it routes to its sub-skills in folders beside it
   (`runtime-generation-setup`, `runtime-generation-validation`, `performance`, `debug-inspection`, `manual-edit`,
   `runtime-generation/low-end-devices`). Read the one it names before acting.
3. The sub-skills drive PCG through the editor's MCP toolsets (`PCGToolset`, `PCGEditor.PCGEditorSubsystem`); use the
   `unreal-mcp` skill and the consuming project's rules for editor access, asset edits and source control.
   The editor also lists these skills through `ToolsetRegistry.AgentSkillToolset` (`ListSkills`, `GetSkills`).

If the resolver fails or the engine has no such file (before 5.9), say so.
