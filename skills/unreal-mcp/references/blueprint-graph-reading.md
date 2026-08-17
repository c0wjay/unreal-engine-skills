# Blueprint Graph Reading and BP-to-C++ Porting

Read this reference before auditing whether a Blueprint implements logic or reconstructing a Blueprint graph in C++.
Unqualified tool names below are `BlueprintTools` methods.

## Ground-truth workflow

1. Resolve authored graphs with `list_graphs`. Collapsed-graph entries need a different reader; `list_functions` is
   only a hint (Discovery pitfalls).
2. Optionally skim the graph DSL to identify likely calls. Never use it as the control-flow or data-flow source of
   truth. See Control-flow rules and Data-pin rules.
3. Locate the function/event entry node and retrieve its connected subgraph with full input/output pin connections.
4. Reconstruct every exec edge literally, using labels or explicit states where the graph needs them. Refactor only
   after the reconstruction covers every exec edge in the connected subgraph.
5. Trace every data pin to its source with `get_node_infos`, following Data-pin rules. Verify function signatures,
   struct fields, Blueprint-only variables, and `ExposeOnSpawn` properties against current C++ source and Blueprint
   variable metadata.
6. Re-read the final native implementation beside the connected subgraph.

## Control-flow rules

Establish execution order from exec pins only: follow `output_pins` with `type_id == "Exec"` through the entry
node's connected subgraph.

- A pure node evaluates where its output is consumed, not at the top-of-function `bind` where the DSL declares it.
- Tell pure from impure by whether the node has an Exec pin, not by DSL formatting.
- Treat an unconnected exec output in `get_node_infos` as a real dead end, commonly an early return.
- Never conclude that a switch or branch case is unhandled from an empty DSL case. Cases wired to one shared target
  print as bare labels, indistinguishable from an unconnected pin. Read the switch node with `get_node_infos` and
  compare its exec `output_pins` `refPath` values instead.
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
- Arity of a `K2Node_PromotableOperator`. An input holding a typed-in literal (`connected_pins: []`) can be omitted,
  inconsistently: a printed literal on one node is not evidence that another has none.
- Arity of a `K2Node_CommutativeAssociativeBinaryOperator` (OR, AND, Add, Multiply). It renders as binary, so every
  input past `B` is dropped even when wired.
- A variable's owning class or member type. `Class|<ClassName>|Get<Member>` is a label, not the node's `self` pin
  type, and it can name a different class that declares a same-named variable.

Resolve each with `get_node_infos`:

- Walk from `find_nodes(graph, title="Return Node")` to the driving node, then read `index_id` on each
  `connected_pins` entry: it is the output pin index on the source node.
- Map `BreakVector2D` as `index_id 0 = X`, `1 = Y`. Add `2 = Z` for `BreakVector`.
- Run `get_node_infos` on every operator node feeding a ported value or condition.
- Count its `input_pins`; the DSL does not carry arity.
- Verify an edit to such a node by re-reading its `input_pins`, never by diffing the DSL before and after.
- Check an input pin's `connected_pins` before its `value`. A wired pin keeps the literal it held before the wire,
  so `value` is the operand only when `connected_pins` is empty.
- Trace every connected input pin back to a real node, collapsing `type_id == "|RerouteNode"` hops through their
  single input.
- Read a getter's `self` input pin `type_id` for the owning class, and its output pin `type_id` for the member type.
- Verify which node an intermediate value is Broken from. A pre-scaled struct of the same type compiles cleanly and
  changes the result.
- Cross-check every resolved type against the signature of whatever consumes it.
- Call `ObjectTools.list_properties` on the Blueprint CDO for any Blueprint reparented onto a native class. It lists
  a Blueprint variable and a native property side by side; their FNames differ, so UE reports no collision.

Do not call `get_connected_subgraph` to disambiguate one node in a pure function graph. Every node there is reachable
from every other node, so it returns the whole graph.

Run `get_node_infos` before accepting a DSL reading that first-principles math contradicts. A working Blueprint is not
evidence that the DSL rendered it completely.

Trace every input before concluding that a code path is unreachable. Matching literals across call sites are not
corroboration: one stale default reads the same at every site wired the same way.

## Discovery pitfalls

- `list_functions` is reliable for authored function graphs and many `BlueprintNativeEvent` overrides with returns, but
  it is not proof that a void event override is absent. Inspect authored graphs and EventGraph entry nodes.
- A Blueprint display name is not a C++ identifier. Verify every call and member in current source.
- A Blueprint name can contain spaces and the DSL strips them, so no DSL rendering is proof of the real `FName`.
  Byte-scan the declaring asset for both spellings before writing the C++ name.
- `list_variables(blueprint)` returns members only. Pass `graph=<asset>:<FunctionName>` to list a function's locals.
- A function-local's authored default is unreadable by every MCP tool, and the getter's output pin reports `""`.
  Do not take that `""` as the value.
- Recover it by byte-scanning the `.uasset` for the exported form of that variable's type, then attributing every hit
  to a node you have already read. The unattributed hit is the local's default.
- A local that is read but never written is a constant, not dead code.
- A Blueprint variable may have no native counterpart. Call `list_variables` before planning to migrate it.
- Tool output reflects the currently compiled parent class. A pending native signature change can make graph metadata
  stale until the USER compiles.
- `read_graph_dsl` throws `Cannot cast type 'K2Node_Composite' to 'Blueprint'` on a collapsed graph. Read that graph
  with `find_nodes` / `get_node_infos` / `get_connected_subgraph` instead: they accept the dotted
  `EventGraph.K2Node_Composite_0.<Name>` path that `list_graphs` returns.
- Do not read the parent `EventGraph` in place of a composite. It does not render composite contents, so a Blueprint
  whose logic lives in composites reads as almost empty.
- Do not treat `find_nodes(EventGraph, "", entry_points_only=True)` as the event list. An event implemented inside a
  composite is absent from it; cross-check against `list_events`.
- Sweep several Blueprints with one `read_graph_dsl` call per graph, not one batched `execute_tool_script`. The
  composite throw surfaces at the tool-transport layer, so the script's `try/except` does not catch it and every
  partial result in the batch is lost.
- Do not recompile, re-save, or shrink the batch in response to the composite throw. Its trigger is the collapsed
  graph in the enumerated list, not asset corruption or a timeout.
- `get_node_infos` throws for a whole batch on one undescribable node, and escapes `try/except` the same way. Fall
  back to `get_connected_subgraph` on the entry node rather than shrinking the batch: it skips the bad node.
- Name the undescribable node by subtracting the `get_connected_subgraph` node set from the `find_nodes(graph, "")`
  set. That difference also contains nodes unreachable from the entry, so confirm each candidate one call at a time.

## Port boundary and handoff

- Ground every claim you make about a graph in pin data from `get_node_infos` or `get_connected_subgraph`, never in
  a DSL rendering. This covers each line of the USER checklist, not only the code you write.
- Check a function's locals before planning to move it.
- Do not plan to turn a function that uses locals into a `BlueprintImplementableEvent` override. An EventGraph has no
  locals, so its get/set nodes break on paste.
- Keep that function in place and add a differently-named native `BlueprintImplementableEvent` that the Blueprint
  forwards to it.
- Name the native event for the notification and the Blueprint function for the action, so the pair does not read as
  a duplicate: `UpdateQuestMarker` forwarding to `Set Quest Marker`.
- Enumerate a Blueprint event's callers with `AssetTools.get_referencers` before deleting it, and put every caller in
  the checklist.
- A stale by-name call in another Blueprint is a runtime `Fatal`, not a compile error, until that caller is
  recompiled: compiling the ported asset proves nothing about its callers.
- Repair caller sites.

## Evidence to retain

Record the asset path, graph name, entry node, relevant branch/Select wiring, and verified native symbols. Name each
verified pin in a comment in the ported code. A large raw subgraph response is a scratch file, not evidence to keep.

Past roughly 100 nodes, render `find_nodes` -> `get_node_infos` to compact text inside
`ProgrammaticToolset.execute_tool_script` instead of returning a raw subgraph, so only the rendering enters context.
If that render throws, fall back to `get_connected_subgraph` and post-process its spilled JSON (Discovery pitfalls).
