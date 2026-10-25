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

- Do not create, edit, compile, save, rename, or delete Blueprint/Widget/Anim Blueprint assets unless the consuming
  project's rules authorize those exact assets (Lyra: `.rules/UNREAL.md` Rule 15 — the USER naming them in the
  current conversation, or a worker's dispatch `Scope`). Without that authorization, use Unreal MCP only to
  inspect them: give the USER an exact ordered Korean editor checklist, then verify the result read-only after they
  perform it. An authorized edit still closes through the consuming project's verification sequence and the
  mutation-safety rules under "Inspect or mutate safely" below.
- Build only through the procedure the consuming project's rules define. Where they define none, do not run or request
  builds: use available static diagnostics and leave compilation to the USER.
- Never modify `Engine/`. Extend through project or plugin code.

## Discover and call tools

Keep Tool Search enabled. Discover and dispatch every ToolsetRegistry method through the three MCP meta-tools:

1. If the relevant domain is unclear, call `list_toolsets`. If it is clear, call `describe_toolset` directly for the likely toolset.
2. Use `describe_toolset` to inspect the candidate toolset and treat its returned schema as the contract.
3. Call `call_tool` with `toolset_name`, `tool_name`, and an `arguments` object matching that schema. `call_tool` always requires `toolset_name`; do not use top-level dispatch or invent flattened native tool names.

If any meta-tool is unavailable, treat the server configuration as incomplete. Ask the USER to enable Tool Search and
restart or refresh the server.

Prefer narrow queries. Serialize Unreal MCP calls: they run against shared editor/game-thread state, and parallel calls
can collide even when they appear independent. Check every returned status before continuing.

## Inspect or mutate safely

- Check PIE and compilation state before editor-only operations.
- **Never edit an asset while PIE is running:** `save_asset` returns `False` and stopping PIE silently reverts the in-memory object to on-disk state. A later save writes the reverted object, permanently losing changes (`asset_edits_made_during_PIE_are_lost_on_stop.md`).
- **Never call `reload_packages` on an asset whose editor is or was open this session:** Blueprint, Anim Blueprint, or a montage alike — the editor crashes with a recursion guard failure even if the script closes that editor first (`reload_packages_on_an_open_blueprint_crashes_the_editor.md`). To discard unsaved changes, quit the editor instead. Verify BP edits with `compile_blueprint` -> `save_asset == True` -> checking `.uasset` mtime moves.
- **Saving DataAssets:** If `save_asset` returns `False` on a DataAsset after scripted property edits, save with `EditorLoadingAndSavingUtils.save_packages(pkgs, only_dirty=False)` (`save_asset_returns_False_use_save_packages.md`).
- **Verifying deletions:** `delete_asset` returning `True` does not guarantee removal (live UObject references block deletion). Always verify with `does_asset_exist` and file existence (`delete_asset_returns_True_without_deleting.md`).
- **Asset discovery traps:** `find_assets(folder_path="")` omits `/IFP_CommonAssets/` and `/InputSystem/`; search those mount points explicitly (`MCP_find_assets_root_folder_misses_two_plugins.md`). `find_assets` with `asset_type` fails silently on native classes (`MCP_find_assets_asset_type_filter_returns_nothing.md`); filter in script via `get_asset_class` or use `tags: {"ParentClass": "Class'...'"} `.
- **Struct array mutations:** `ObjectTools.set_properties` fails or corrupts arrays if size and content change in one call (`MCP_set_properties_fails_on_struct_array_resize.md`). Grow one element at a time echoing existing elements verbatim, or clear to `[]` first.
- Create a recovery point before permitted bulk mutation and save only after confirming success.
- Treat Python/programmatic editor execution as privileged bulk access. Keep its scope explicit and never use it to
  bypass project mutation rules.
- After a permitted mutation, re-read the affected asset or editor state rather than trusting the write response alone.
- A success return is not proof. A tool can return its normal success value while the operation failed, and a save
  call can report true after writing nothing. Verify by re-reading the state the tool claims to have changed.
- A silent log is not proof either. The operation may never have been triggered, and shader or asset compilation is
  asynchronous, so scraping the log immediately after the call says nothing about the result.
- Reading a struct, array, or map property hands back a copy. Assign the modified value back through every nesting
  level, or the write is silently discarded while every call still reports success.
- Reading an asset or graph through Unreal MCP marks the package dirty. Do not treat `is_dirty == true` as evidence the USER forgot to save (`MCP_read_only_inspection_marks_assets_dirty.md`).

## Live PIE probing & runtime measurement standards

When measuring or capturing live PIE state via Python (`ue_execute_python` / `register_slate_post_tick_callback`):

- **Callback globals & imports:** Callbacks lose script `__globals__` once execution ends. Import `unreal` and `builtins` **inside** the callback body and store state on `builtins` or `unreal.MY_STATE`. Always unregister callback handles on completion (`python_callback_from_ue_execute_python_has_empty_globals.md`).
- **Never store UObjects in module/global state (Hard Limit):** Python holds UObjects as GC roots through `FPyReferenceCollector`. Caching an actor or component roots the whole PIE world, stalling the editor on stop with `PIE: Error: World ... from PIE level still referenced` (`editor_python_probing_a_live_pie_ragdoll.md`). Store **path strings** (`get_path_name()`) and resolve inside the callback via `unreal.find_object(None, path)`. Never rescan every tick with `get_all_actors_of_class`.
- **Do not `set_editor_property` on simulating meshes:** Writing properties on a simulating skeletal mesh triggers `PostEditChangeProperty`, resets physics state, and kills simulation (`is_any_simulating_physics() -> False`). Change settings between ragdolls or via C++.
- **Background throttling:** Unfocused editor windows throttle down to `dt ~= 0.125s` (~8 samples/s; timers ~3 Hz). State sign flips remain measurable, but fine trajectories do not.
- **Check game pause:** Check `GameplayStatics.is_game_paused` and verify `get_time_seconds` advances. Timer-driven components freeze while paused (`runtime_property_change_does_nothing_while_PIE_is_paused.md`).
- **Component space for pop measurements:** Sample bone transforms in component space (`get_socket_transform(bone, RTS_COMPONENT)`). Rank displacement frames by positions relative to the root, never by Euler yaw/roll deltas (pitch ±90° suffers gimbal lock).


## Read Blueprint graphs and port to C++

For Blueprint audits, override detection, graph reconstruction, or BP-to-C++ work, read
`references/blueprint-graph-reading.md` before inspecting the graph. Its connected-pin workflow is mandatory because
the graph DSL is lossy on exec pins (execution order, dead ends, branch polarity, Select options) and on data pins
(collapsed multi-output nodes, dropped operands, mislabelled variable owners). Never port anything from the DSL alone.

Enumerate graphs with `list_graphs`. `read_graph_dsl` throws on a `.K2Node_Composite` entry; read those with
`find_nodes` / `get_node_infos`, which accept the dotted graph path. Never substitute the parent `EventGraph` - it
does not render composite contents.

## Load project Agent Skills

When the project is unfamiliar, query `AgentSkillToolset` for registered Unreal Agent Skills. Load a relevant skill's
full instructions before acting. Unreal Agent Skills are editor-registered knowledge objects; they are distinct from
this Claude Code harness skill.

## References

- `references/blueprint-graph-reading.md`: reliable Blueprint audit and BP-to-C++ reconstruction.
- `references/setup.md`: first-time server/client configuration, including the Project-specific plugin and port policy.
- `references/operations.md`: console commands, Tool Search workflow, and recovery steps.

## Companion skills

- Use `create-toolset` to add or redesign AI-callable Unreal toolsets.
- Use `unreal-skill` to create or revise Unreal Agent Skills registered inside the editor.
