---
name: unreal-build-diagnosis
description: "Diagnose Unreal Engine C++ compile, link and UnrealBuildTool failures, and check a C++ or .Build.cs change before building it, by following the engine's own unreal-build-diagnosis skill for the project's engine version. Use when a build fails, is slow, rebuilds everything, or cannot find a module, plugin or SDK, and before building a change to a .Build.cs, .uplugin, header or reflected type."
---

# Unreal build diagnosis (engine skill redirector)

The guidance ships with the engine (UE 5.9 and later) and changes with each engine version, so this file carries no
copy of it.

1. Find the engine root from the project: `python -I "<this skill's base directory>/../../scripts/find_engine_root.py"
   "<project .uproject>"`. It prints the folder that holds `Engine/`.
2. Read `<root>/Engine/Extras/AgentTools/Skills/unreal-build-diagnosis/SKILL.md` in full.
3. Take from it the reading parts: the pre-build read of a change (each `#include` against `.Build.cs` dependencies,
   `<MODULE>_API` exports, reflected types) and how to read a failure (the first error per file; a header-tool error
   hides every compile and link error behind it, so expect another round after the fix).
4. Its `RunUBT.bat` / `RunUAT.bat` commands are builds. Run one only when the consuming project's rules allow that
   path. Where they define a build procedure (Lyra: `.rules/BUILD.md` Rule 23), build only through it.

If the resolver fails or the engine has no such file (before 5.9), say so, and read the compiler output from its first
error.
