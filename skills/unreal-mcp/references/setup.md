# Unreal MCP Setup

Read this only when a project has not been connected or the configured client cannot reach the live editor. Inspect the
project's existing plugin list and client configuration before changing anything. This reference is the connection
source of truth; do not rely on retired team setup notes.

## Connection contract

- The Unreal MCP server runs inside the local Unreal Editor. It is available only while that editor is running.
- This project uses `http://127.0.0.1:8123/mcp`. `127.0.0.1` is loopback-only, so each machine runs and configures
  its own editor server.
- Restarting the editor or server invalidates active MCP sessions. Reconnect the client before making another call.

## 1. Enable the server and required toolsets

Enable `ModelContextProtocol` in the `.uproject`, then enable only the toolset plugins the project needs. Do not assume
the `AllToolsets` umbrella is safe: it can activate expensive or experimental dependencies.

- The project already enables `ModelContextProtocol` plus an explicit toolset list.
- Never re-enable `AllToolsets` or `SemanticSearchToolset`; the latter caused the editor-start asset-index freeze.
- Do not modify Engine plugin files. Project/plugin descriptors and local configuration are the extension points.

## 2. Configure server startup

Persistent per-machine settings live in:

`<Project>/Saved/Config/<Platform>Editor/EditorPerProjectUserSettings.ini`

```ini
[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]
bAutoStartServer=True
bEnableToolSearch=True
```

Keep `bEnableToolSearch=True`: clients discover toolsets through `list_toolsets`, `describe_toolset`, and `call_tool`.
Optional settings include `ServerPortNumber` and `ServerUrlPath`. These are machine-local and must not be presented as
shared repository state.

Project's configured endpoint is `http://127.0.0.1:8123/mcp`. Check the existing setting before changing it. To start
the configured server immediately, run `ModelContextProtocol.StartServer 8123` from the Unreal Editor console.

## 3. Configure each client

Claude-compatible clients use `.mcp.json`; Codex uses project `.codex/config.toml`. Keep both pointed at the same live
endpoint, but do not overwrite an existing configuration blindly.

Claude-style configuration:

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "type": "http",
      "url": "http://127.0.0.1:8123/mcp"
    }
  }
}
```

Codex configuration:

```toml
[mcp_servers.unreal]
url = "http://127.0.0.1:8123/mcp"
```

The editor command `ModelContextProtocol.GenerateClientConfig <client>` can generate or merge supported client
configuration. Review its destination and diff; the Codex writer refuses to overwrite an existing config.

## 4. Verify without building

1. Launch the editor and confirm the MCP server startup message in the Output Log.
2. Confirm the configured endpoint connects.
3. Start Tool Search with `list_toolsets`, then inspect one result with `describe_toolset`.
4. If the editor or server restarted, reconnect the client so it initializes a fresh MCP session.
5. If toolsets are missing, use `references/operations.md`; do not run a build as a connectivity diagnostic.
