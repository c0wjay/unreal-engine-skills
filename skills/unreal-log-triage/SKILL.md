---
name: unreal-log-triage
description: "Find the real cause in an Unreal Engine log, crash or failed run without reading the whole log, by following the engine's own unreal-log-triage skill for the project's engine version. Use when a build, cook, editor, commandlet or game run failed, crashed, hung or 'worked but did nothing', when asked what went wrong in a log, when crash folders or ensures pile up in Saved/Crashes, or when comparing a bad run with a good one."
---

# Unreal log triage (engine skill redirector)

The guidance ships with the engine (UE 5.9 and later) and changes with each engine version, so this file carries no
copy of it.

1. Find the engine root from the project: `python -I "<this skill's base directory>/../../scripts/find_engine_root.py"
   "<project .uproject>"`. It prints the folder that holds `Engine/`.
2. Read `<root>/Engine/Extras/AgentTools/Skills/unreal-log-triage/SKILL.md` in full and follow it. Its scripts
   (`ue_log_digest.py`, `ue_crash_triage.py`) are in `<root>/Engine/Extras/AgentTools/`; run them with `python -I`.
   Both only read logs and crash folders.
3. The consuming project's rules win where they differ (which logs exist, who may run what). On a launcher-installed
   engine UnrealBuildTool writes `%LOCALAPPDATA%\UnrealBuildTool\Log.txt`, not `<root>/Engine/Programs/UnrealBuildTool/Log.txt`.

If the resolver fails or the engine has no such file (before 5.9), say so, and read the log from its first error.
