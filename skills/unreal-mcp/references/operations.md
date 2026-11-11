# Operations: Console Commands, Settings, Recovery

Read this when something is misbehaving with the MCP server (tools missing, port collision, stale tool registry), or when you need a non-default configuration.

## Console commands

Run these from the Unreal Editor console (`~`).

| Command                                              | Use it for                                                                                               |
|------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| `ModelContextProtocol.StartServer [port]`            | Start the MCP server. Pass a port to override the default (e.g. when 8000 is in use).                    |
| `ModelContextProtocol.StopServer`                    | Stop the server. Useful if the registry is in a bad state and you want a clean restart.                  |
| `ModelContextProtocol.RefreshTools`                  | Re-register every toolset. Run this after the user enables a new toolset plugin.                         |
| `ModelContextProtocol.GenerateClientConfig ClaudeCode` | Regenerate `.mcp.json` from the current server port and URL.                                             |

## Tool Search workflow

Keep `bEnableToolSearch=True` (the default). On UE 5.9 `tools/list` exposes `list_toolsets`, `describe_toolsets`,
`describe_tools`, and `call_tool`; use them in that order to discover a toolset, list its tools, read the schema of the
ones you call, and dispatch. This keeps the tool catalog
small and makes the current schema authoritative. Do not disable Tool Search or depend on flattened native tool names.

## Troubleshooting matrix

| Symptom                                               | What to do                                                                                                                                                                                                                                                                                                          |
|-------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `unreal` (the `.mcp.json` server key) not in `/mcp`, or discovery errors | The editor isn't running, or the MCP server isn't started. Ask the user to launch the editor and run `ModelContextProtocol.StartServer` from the console, or to relaunch it with `-ModelContextProtocolStartServer`. Then check the Output Log for startup errors. Do not enable `bAutoStartServer` to fix this — it breaks cooking (`setup.md`).                                                               |
| The server answers a direct probe, but its tools are missing or only partly present in this session | The host client froze at session start, not the server. A failed initial connection is retried a few times and then marked failed for good, and a server declaring `capabilities.tools.listChanged = false` never refreshes its tool list — so starting the editor mid-session, or finishing indexing late, changes nothing. Neither a hook nor the agent can recover it; ask the USER to reconnect that server from `/mcp`. Judge by whether a specific required tool is present, never by tool count. |
| Editor logs "Failed to listen on port"                | Another process holds the default port. Change `ServerPortNumber` in the per-user `EditorPerProjectUserSettings.ini` (see `setup.md`), or pass `-ModelContextProtocolPort=<port>` on the next launch; restart the editor, and re-run `ModelContextProtocol.GenerateClientConfig ClaudeCode` to refresh `.mcp.json`. |
| HTTP `400 Bad Request` after an editor/server restart | The client retained an `Mcp-Session-Id` from the previous server process. Reconnect or restart that client so it sends a fresh `initialize`; do not retry calls with the stale session. |
| A client on another machine cannot connect             | The project endpoint uses `127.0.0.1`, which is local to the machine running the editor. Run the editor MCP server and configure the same endpoint independently on that machine. |
| A toolset you expect (e.g. `NiagaraTools`) is missing | Run `ModelContextProtocol.RefreshTools`. If still missing, check whether its specific plugin is enabled in the `.uproject` (most toolset plugins are off by default; UE 5.9 moved the Blueprint graph tools into `BlueprintToolsets`). Never solve this by re-enabling `AllToolsets` or `SemanticSearchToolset`.                                                                                                               |
| `list_toolsets`, `describe_toolsets`, `describe_tools`, or `call_tool` is unavailable | Verify `bEnableToolSearch=True` in the per-user settings, restart or refresh the MCP server, then retry discovery. |
| A Tool Search call disconnects or fails                | Keep Tool Search enabled. Reconnect the client to obtain a fresh session, check the Unreal Output Log for the exact failure, then retry `list_toolsets → describe_toolsets → describe_tools → call_tool`. Do not switch to flattened tool names or disable Tool Search as a workaround. |
| Tool calls hang or return errors                      | Editor may be busy compiling, loading a level, or in PIE. Wait and retry. For long compiles, prefer `LiveCodingToolset.CompileLiveCoding`. It returns when the compile actually finishes.                                                                                                                           |
| `AIAssistantToolset.GetDockedContext` returns empty   | The Claude Code tab must be docked inside an asset editor (Blueprint, Material, etc.) to provide docked context. If undocked, that tool has nothing to report.                                                                                                                                                      |
| Sequential tool calls collide                         | Tool calls execute on the game thread. Don't issue them in parallel, even when they look independent. Serialize.                                                                                                                                                                                                    |

Asset-mutation and PIE-probe traps (`reload_packages`, saves during PIE, DataAsset saves, `delete_asset`, `find_assets`,
struct arrays, Python callbacks) are in `SKILL.md` → "Inspect or mutate safely" and "Live PIE probing".

