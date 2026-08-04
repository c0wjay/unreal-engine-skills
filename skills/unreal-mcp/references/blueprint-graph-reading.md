# Blueprint Graph Reading and BP-to-C++ Porting

Read this reference before auditing whether a Blueprint implements logic or reconstructing a Blueprint graph in C++.

## Ground-truth workflow

1. Resolve authored graphs with the Blueprint graph/list tools. Use `list_functions` only as a hint: it can omit void
   `BlueprintImplementableEvent` overrides implemented as EventGraph nodes.
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

The DSL is lossy on data pins as well as exec pins, and both data losses are silent.

- Do not read a component off the DSL. Every output of a multi-output node collapses to one token, so
  `BreakVector2D`'s `X` and `Y` render identically.
- Do not infer operator arity from the DSL. A `K2Node_PromotableOperator` input holding a typed-in literal
  (`connected_pins: []`) can be omitted entirely, and the omission is inconsistent: a printed literal on one node is
  not evidence that another node has none.
- Do not call `get_connected_subgraph` to disambiguate a node in a pure function graph. Every node there is reachable
  from every other node, so it returns the whole graph.
- Resolve an ambiguous value with `get_node_infos` instead. Walk from `find_nodes(graph, title="Return Node")` to the
  driving node, then read `index_id` on each `connected_pins` entry: it is the output pin index on the source node.
- Map `BreakVector2D` as `index_id 0 = X`, `1 = Y`. Add `2 = Z` for `BreakVector`.
- Run `get_node_infos` on every arithmetic node feeding a ported value.
- Read each `input_pins` entry's `value` even when its `connected_pins` is empty.
- Verify which node an intermediate value is Broken from. A pre-scaled struct of the same type compiles cleanly and
  changes the result.
- Run `get_node_infos` before accepting a DSL reading that first-principles math contradicts. A working Blueprint is
  not evidence that the DSL rendered it completely.
- Limit pin walks to one `get_node_infos` pair per ambiguous value, and name the verified pin in a comment in the
  ported code.

## Discovery pitfalls

- `list_functions` is reliable for authored function graphs and many `BlueprintNativeEvent` overrides with returns, but
  it is not proof that a void event override is absent. Inspect authored graphs and EventGraph entry nodes.
- A Blueprint display name is not a C++ identifier. Verify every call and member in current source.
- A Blueprint variable may have no native counterpart. Use the Blueprint variable query before planning its migration.
- Tool output reflects the currently compiled parent class. A pending native signature change can make graph metadata
  stale until the USER compiles.

## Evidence to retain

Record the asset path, graph name, entry node, relevant branch/Select wiring, and verified native symbols. Large raw
subgraph responses are scratch evidence: keep them only under `Saved/Temp/AI/TEAM_XXX/` and never reconcile
them into source control.
