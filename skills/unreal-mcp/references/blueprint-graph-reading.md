# Blueprint Graph Reading and BP-to-C++ Porting

Read this reference before auditing whether a Blueprint implements logic or reconstructing a Blueprint graph in C++.
Unqualified tool names below are UE 5.9 `BlueprintToolsets.BlueprintToolset` tools (the `BlueprintToolsets` plugin
must be enabled); `read_graph_dsl` is `editor_toolset.toolsets.blueprint.BlueprintDslTools`. Read argument and result
field names with `describe_tools`. The pitfalls below were first measured on UE 5.8's Python `BlueprintTools`
(snake_case names); re-check one on your engine before you build a conclusion on it.

## Ground-truth workflow

1. Resolve authored graphs with `ListGraphs`. Collapsed-graph entries need a different reader; `ListFunctions` is
   only a hint (Discovery pitfalls).
2. Optionally skim the graph DSL to identify likely calls. Never use it as the control-flow or data-flow source of
   truth. See Control-flow rules and Data-pin rules.
3. Locate the function/event entry node and retrieve its connected subgraph with full input/output pin connections.
4. Reconstruct every exec edge literally, using labels or explicit states where the graph needs them. Refactor only
   after the reconstruction covers every exec edge in the connected subgraph.
5. Trace every data pin to its source with `GetNodeInfos`, following Data-pin rules. Verify function signatures,
   struct fields, Blueprint-only variables, and `ExposeOnSpawn` properties against current C++ source and Blueprint
   variable metadata.
6. Re-read the final native implementation beside the connected subgraph.

## Control-flow rules

Establish execution order from exec pins only: follow `outputPins` with `typeId == "Exec"` through the entry
node's connected subgraph.

- A pure node evaluates where its output is consumed, not at the top-of-function `bind` where the DSL declares it.
- Tell pure from impure by whether the node has an Exec pin, not by DSL formatting.
- Treat an unconnected exec output in `GetNodeInfos` as a real dead end, commonly an early return.
- Never conclude that a switch or branch case is unhandled from an empty DSL case. Cases wired to one shared target
  print as bare labels, indistinguishable from an unconnected pin. Read the switch node with `GetNodeInfos` and
  compare its exec `outputPins` `refPath` values instead.
- Preserve the wired `then`/`else` polarity of every branch.
- Preserve `K2Node_ExecutionSequence` output order.
- A `K2Node_FunctionResult` reached from one `ExecutionSequence` output returns from the whole function; later
  outputs never run.
- Treat `K2Node_FunctionResult` and its connected value pins as the return contract.
- Dump every Select node's input pins by name before porting it. The DSL can print one value for several options.
- On an enum Select the option pin names are the enum entries.
- On a Boolean Select `false` selects Option 0 and `true` selects Option 1; confirm which value each option carries.

## Data-pin rules

The DSL is lossy on data pins as well as exec pins, and every data loss is silent.

Never take these from the DSL:

- A component. Every output of a multi-output node collapses to one token, so `BreakVector2D`'s `X` and `Y` render
  identically.
- Arity of a `K2Node_PromotableOperator`. An input holding a typed-in literal (`connectedPins: []`) can be omitted,
  inconsistently: a printed literal on one node is not evidence that another has none.
- Arity of a `K2Node_CommutativeAssociativeBinaryOperator` (OR, AND, Add, Multiply). It renders as binary, so every
  input past `B` is dropped even when wired.
- A variable's owning class or member type. `Class|<ClassName>|Get<Member>` is a label, not the node's `self` pin
  type, and it can name a different class that declares a same-named variable.

Resolve each with `GetNodeInfos`:

- Walk from `FindNodes(graph, title="Return Node")` to the driving node, then read `indexId` on each
  `connectedPins` entry: it is the output pin index on the source node.
- Map `BreakVector2D` as `indexId 0 = X`, `1 = Y`. Add `2 = Z` for `BreakVector`.
- Run `GetNodeInfos` on every operator node feeding a ported value or condition.
- Count its `inputPins`; the DSL does not carry arity.
- Verify an edit to such a node by re-reading its `inputPins`, never by diffing the DSL before and after.
- Check an input pin's `connectedPins` before its `value`. A wired pin keeps the literal it held before the wire,
  so `value` is the operand only when `connectedPins` is empty.
- Trace every connected input pin back to a real node, collapsing `typeId == "|RerouteNode"` hops through their
  single input.
- Read a getter's `self` input pin `typeId` for the owning class, and its output pin `typeId` for the member type.
- Verify which node an intermediate value is Broken from. A pre-scaled struct of the same type compiles cleanly and
  changes the result.
- Cross-check every resolved type against the signature of whatever consumes it.
- Do not treat a wired input pin as proof that its destination property still exists. UE keeps a removed or renamed
  property's pin alive for as long as something stays linked into it, and that orphan discards the value at compile
  time. Some assets log `In use pin '<Name>' no longer exists on node`; others log nothing, so silence is not
  evidence.
- Suspect an orphan when one node carries two near-identical pin names (`TargetArmLength` beside
  `Target Arm Length`), or when a pin's precision disagrees with the class: a Blueprint `float` is
  double-precision, a C++ `float` property single.
- Confirm against the destination class's CDO, not against the node: read the property off the CDO and check
  `Config/*.ini` `+PropertyRedirects=` before concluding it is gone.
- When the property is gone, the shipped behaviour is "the value never arrived". Port the live pin's literal and
  drop the wire. Restoring the value is a behaviour change — record it as a TODO for the USER instead.
- Call `EditorToolset.ObjectToolset` `ListProperties` on the Blueprint CDO for any Blueprint reparented onto a native
  class. It lists a Blueprint variable and a native property side by side; their FNames differ, so UE reports no
  collision.

Do not call `GetConnectedSubgraph` to disambiguate one node in a pure function graph. Every node there is reachable
from every other node, so it returns the whole graph.

Run `GetNodeInfos` before accepting a DSL reading that first-principles math contradicts. A working Blueprint is not
evidence that the DSL rendered it completely.

Trace every input before concluding that a code path is unreachable. Matching literals across call sites are not
corroboration: one stale default reads the same at every site wired the same way.

## Discovery pitfalls

- `read_graph_dsl` renders only exec-reachable flow, so a node with no incoming exec connection is omitted entirely.
  Never build a reference or migration list from graph text.
- Drive every reference sweep from `EditorToolset.AssetToolset` `GetReferencers`. It reads the asset registry and is
  the ground truth for what still points at an asset.
- To find the referencing nodes inside a Blueprint the referencer list flags, run `FindNodes(graph)` ->
  `GetNodeInfos` and scan `typeId` plus every pin's `value` and `typeId`. A class literal held in a pin default
  is invisible to the DSL and to a title search alike.
- Report orphaned nodes to the USER as a design call. Do not delete them as silent cleanup.
- Reading an asset dirties its package, so `IsDirty == true` after your own inspection carries no information.
  Never report it as "the USER did not save" — ask. `GetReferencers` reads the saved registry and is unaffected.
- `ListFunctions` is reliable for authored function graphs and many `BlueprintNativeEvent` overrides with returns, but
  it is not proof that a void event override is absent. Inspect authored graphs and EventGraph entry nodes.
- A Blueprint display name is not a C++ identifier. Verify every call and member in current source.
- A Blueprint name can contain spaces and the DSL strips them, so no DSL rendering is proof of the real `FName`.
  Byte-scan the declaring asset for both spellings before writing the C++ name.
- `ListVariables(blueprint)` returns members only. Pass `scope="Local"` with `graph` = the function graph to list that
  function's locals.
- A function-local's authored default is unreadable by every MCP tool, and the getter's output pin reports `""`.
  Do not take that `""` as the value.
- Recover it by byte-scanning the `.uasset` for the exported form of that variable's type, then attributing every hit
  to a node you have already read. The unattributed hit is the local's default.
- A local that is read but never written is a constant, not dead code.
- A Blueprint variable may have no native counterpart. Call `ListVariables` before planning to migrate it.
- Tool output reflects the currently compiled parent class. A pending native signature change can make graph metadata
  stale until the USER compiles.
- `read_graph_dsl` throws `Cannot cast type 'K2Node_Composite' to 'Blueprint'` on a collapsed graph. Read that graph
  with `FindNodes` / `GetNodeInfos` / `GetConnectedSubgraph` instead: they accept the dotted
  `EventGraph.K2Node_Composite_0.<Name>` path that `ListGraphs` returns.
- Do not read the parent `EventGraph` in place of a composite. It does not render composite contents, so a Blueprint
  whose logic lives in composites reads as almost empty.
- Do not treat `FindNodes(EventGraph, bEntryPointsOnly=True)` as the event list. An event implemented inside a
  composite is absent from it; cross-check against `ListEvents`.
- Sweep several Blueprints with one `read_graph_dsl` call per graph, not one batched script. The composite throw
  surfaces at the tool-transport layer, so the script's `try/except` does not catch it and every partial result in the
  batch is lost.
- Do not recompile, re-save, or shrink the batch in response to the composite throw. Its trigger is the collapsed
  graph in the enumerated list, not asset corruption or a timeout.
- `GetNodeInfos` throws for a whole batch on one undescribable node, and escapes `try/except` the same way. Fall
  back to `GetConnectedSubgraph` on the entry node rather than shrinking the batch: it skips the bad node.
- Name the undescribable node by subtracting the `GetConnectedSubgraph` node set from the `FindNodes(graph)`
  set. That difference also contains nodes unreachable from the entry, so confirm each candidate one call at a time.

## Port boundary and handoff

- Ground every claim you make about a graph in pin data from `GetNodeInfos` or `GetConnectedSubgraph`, never in
  a DSL rendering. This covers each line of the USER checklist, not only the code you write.
- Check a function's locals before planning to move it.
- Do not plan to turn a function that uses locals into a `BlueprintImplementableEvent` override. An EventGraph has no
  locals, so its get/set nodes break on paste.
- Keep that function in place and add a differently-named native `BlueprintImplementableEvent` that the Blueprint
  forwards to it.
- Name the native event for the notification and the Blueprint function for the action, so the pair does not read as
  a duplicate: `UpdateQuestMarker` forwarding to `Set Quest Marker`.
- Enumerate a Blueprint event's callers with `EditorToolset.AssetToolset` `GetReferencers` before deleting it, and put
  every caller in the checklist.
- A stale by-name call in another Blueprint is a runtime `Fatal`, not a compile error, until that caller is
  recompiled: compiling the ported asset proves nothing about its callers.
- Repair the caller sites. Do not silence a renamed event with a `[CoreRedirects]` `+FunctionRedirects=` entry: the
  native function's auto display name makes the repaired graph look identical either way, so a redirect only hides
  the stale node.

## Evidence to retain

Record the asset path, graph name, entry node, relevant branch/Select wiring, and verified native symbols. Name each
verified pin in a comment in the ported code. A large raw subgraph response is a scratch file, not evidence to keep.

Past roughly 100 nodes, render `FindNodes` -> `GetNodeInfos` to compact text inside one
`PythonScriptingTools.execute_python` script (`await call_tool(...)`, then return only the rendering) instead of
returning a raw subgraph, so only the rendering enters context. If that render throws, fall back to
`GetConnectedSubgraph` and post-process its spilled JSON (Discovery pitfalls).
