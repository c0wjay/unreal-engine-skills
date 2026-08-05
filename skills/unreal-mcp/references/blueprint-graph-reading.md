# Blueprint Graph Reading and BP-to-C++ Porting

Read this reference before auditing whether a Blueprint implements logic or reconstructing a Blueprint graph in C++.

## Ground-truth workflow

1. Resolve authored graphs with `list_graphs`. Collapsed-graph entries need a different reader (Discovery pitfalls).
   Use `list_functions` only as a hint: it can omit void `BlueprintImplementableEvent` overrides implemented as
   EventGraph nodes.
2. Optionally skim the graph DSL to identify likely calls. Never use it as the control-flow or data-flow source of
   truth. See Data-pin rules.
3. Locate the function/event entry node and retrieve its connected subgraph with full input/output pin connections.
4. Reconstruct every exec edge literally. Start with labels or equivalent explicit states if needed, then refactor only
   after semantic parity is visible.
5. Trace every data pin to its source with `get_node_infos`, following Data-pin rules. Verify function signatures,
   struct fields, Blueprint-only variables, and `ExposeOnSpawn` properties against current C++ source and Blueprint
   variable metadata.
6. Re-read the final native implementation beside the connected subgraph. Deliver any required Blueprint cleanup as an
   ordered Korean USER checklist and verify it read-only after the USER applies it.

## Control-flow rules

- An unconnected exec output is a real dead end, commonly an early return. Do not treat it as a no-op.
- Preserve the wired `then`/`else` polarity of every branch.
- Preserve `K2Node_ExecutionSequence` output order.
- Treat `K2Node_FunctionResult` and its connected value pins as the return contract.
- For Boolean Select nodes, `false` selects Option 0 and `true` selects Option 1. Confirm the actual option wiring.

## Data-pin rules

The DSL is lossy on data pins as well as exec pins, and every data loss is silent.

Never take these from the DSL:

- A component. Every output of a multi-output node collapses to one token, so `BreakVector2D`'s `X` and `Y` render
  identically.
- Operator arity. A `K2Node_PromotableOperator` input holding a typed-in literal (`connected_pins: []`) can be omitted
  entirely, and the omission is inconsistent: a printed literal on one node is not evidence that another has none.
- A variable's owning class or member type. `Class|<ClassName>|Get<Member>` is a label, not the node's `self` pin
  type, and it can name a different class that declares a same-named variable.

Resolve each with `get_node_infos`:

- Walk from `find_nodes(graph, title="Return Node")` to the driving node, then read `index_id` on each
  `connected_pins` entry: it is the output pin index on the source node.
- Map `BreakVector2D` as `index_id 0 = X`, `1 = Y`. Add `2 = Z` for `BreakVector`.
- Run `get_node_infos` on every arithmetic node feeding a ported value.
- Check an input pin's `connected_pins` before its `value`. A wired pin keeps the literal it held before the wire,
  so `value` is the operand only when `connected_pins` is empty.
- Trace every connected input pin back to a real node, collapsing `type_id == "|RerouteNode"` hops through their
  single input.
- Read a getter's `self` input pin `type_id` for the owning class, and its output pin `type_id` for the member type.
- Verify which node an intermediate value is Broken from. A pre-scaled struct of the same type compiles cleanly and
  changes the result.
- Cross-check every resolved type against the signature of whatever consumes it.
- Call `ObjectTools.list_properties` on the Blueprint CDO when a Blueprint variable and a native property may both
  exist. Their FNames differ after a reparent, so UE reports no collision.

Do not call `get_connected_subgraph` to disambiguate a node in a pure function graph. Every node there is reachable
from every other node, so it returns the whole graph.

Run `get_node_infos` before accepting a DSL reading that first-principles math contradicts. A working Blueprint is not
evidence that the DSL rendered it completely.

Trace every input before concluding that a code path is unreachable. Matching literals across call sites are not
corroboration: one stale default reads the same at every site wired the same way.

Limit pin walks to one `get_node_infos` pair per ambiguous value, and name the verified pin in a comment in the ported
code.

## Discovery pitfalls

- `list_functions` is reliable for authored function graphs and many `BlueprintNativeEvent` overrides with returns, but
  it is not proof that a void event override is absent. Inspect authored graphs and EventGraph entry nodes.
- A Blueprint display name is not a C++ identifier. Verify every call and member in current source.
- A Blueprint variable may have no native counterpart. Use the Blueprint variable query before planning its migration.
- Tool output reflects the currently compiled parent class. A pending native signature change can make graph metadata
  stale until the USER compiles.
- `read_graph_dsl` throws `Cannot cast type 'K2Node_Composite' to 'Blueprint'` on a collapsed graph. Read that graph
  with `find_nodes` / `get_node_infos` / `get_connected_subgraph` instead: they accept the dotted
  `EventGraph.K2Node_Composite_0.<Name>` path that `list_graphs` returns.
- Do not read the parent `EventGraph` in place of a composite. It does not render composite contents, so a Blueprint
  whose logic lives in composites reads as almost empty.
- Do not treat `find_nodes(EventGraph, "", entry_points_only=True)` as the event list. An event implemented inside a
  composite is absent from it; cross-check against `list_events`.
- Sweep several Blueprints with one `read_graph_dsl` call per graph, not one batched `execute_tool_script`. That throw
  surfaces at the tool-transport layer, so the script's `try/except` does not catch it and every partial result in the
  batch is lost.
- Do not recompile, re-save, or shrink the batch in response to that throw. The trigger is the collapsed graph in the
  enumerated list, not asset corruption or a timeout.

## Evidence to retain

Record the asset path, graph name, entry node, relevant branch/Select wiring, and verified native symbols. Large raw
subgraph responses are scratch evidence: keep them only under `Saved/Temp/AI/TEAM_XXX/` and never reconcile
them into source control.

Past roughly 100 nodes, render `find_nodes` -> `get_node_infos` to compact text inside
`ProgrammaticToolset.execute_tool_script` instead of returning a raw subgraph, so only the rendering enters context.
