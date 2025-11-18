"""AST DOT exporter.

Provides ASTDotExporter.to_dot(node) which accepts ASTNode-like objects or
lists of such objects. The exporter intentionally avoids importing the
parser's ASTNode class to prevent circular imports; it uses duck-typing
by checking for a `nodetype` attribute.
"""
from typing import Any


class ASTDotExporter:
    """Export AST-like trees to Graphviz DOT format.

    The exporter binary-izes n-ary children into left/right groups using
    dashed connector nodes so tree shapes are easier to inspect.
    """
    def __init__(self):
        # Initialize writer state:
        # - lines: list of DOT lines being built
        # - counter: simple integer counter stored in dict for mutability
        # - ids: mapping from object id() -> generated node name
        self.lines = ['digraph AST {', '  node [shape=box];']
        self.counter = {'i': 0}
        self.ids = {}

    def nid(self, obj: Any) -> str:
        # Return a stable DOT node id for a Python object.
        # If we've already assigned one, reuse it. Otherwise create a new
        # sequential id (n1, n2, ...), store it in the `ids` map and return it.
        if id(obj) in self.ids:
            return self.ids[id(obj)]
        self.counter['i'] += 1
        self.ids[id(obj)] = f'n{self.counter["i"]}'
        return self.ids[id(obj)]

    def new_id(self) -> str:
        # Generate a fresh anonymous DOT id (not tied to a Python object)
        self.counter['i'] += 1
        return f'n{self.counter["i"]}'

    def escape(self, s: Any) -> str:
        # Escape double-quotes so strings can be safely embedded in DOT labels
        return str(s).replace('"', '\\"')

    def make_leaf(self, label: Any) -> str:
        # Create a DOT node that represents a literal/leaf value (like a
        # variable name or literal string/number) and append it to lines.
        lid = self.new_id()
        self.lines.append(f'  {lid} [label="{self.escape(label)}"];')
        return lid

    def make_conn(self) -> str:
        # Create a small connector node (dashed, labeled '·') used to group
        # right-hand items when binary-izing N-ary children. Returns its id.
        cid = self.new_id()
        self.lines.append(f'  {cid} [label="·", style="dashed"];')
        return cid

    def _is_ast_like(self, obj: Any) -> bool:
        # Minimal duck-typing check: an AST-like object must expose
        # `nodetype` and `children` attributes. This allows the exporter to
        # work without importing the ASTNode class directly (avoids cycles).
        return hasattr(obj, 'nodetype') and hasattr(obj, 'children')

    def emit_child_edge(self, parent_id: str, child: Any) -> None:
        # Emit an edge from parent to child. If the child is AST-like, create
        # (or reuse) a node id for it and recurse into its subtree. If it's a
        # plain value, create a leaf node for the value instead.
        if self._is_ast_like(child):
            cid = self.nid(child)
            self.lines.append(f'  {parent_id} -> {cid};')
            self.walk(child)
        else:
            leaf_id = self.make_leaf(child)
            self.lines.append(f'  {parent_id} -> {leaf_id};')

    def attach_children_binary(self, parent_id: str, children: list) -> None:
        # Attach children to `parent_id` while converting an N-ary list of
        # children into a binary-shaped structure suitable for clear DOT
        # visualization. Steps:
        # 1. Flatten any nested lists by one level (productions may return
        #    lists of nodes).
        # 2. Handle special cases: 0 children -> nothing, 1 child -> direct
        #    edge, 2 children -> two direct edges.
        # 3. For 3+ children, create connector nodes so each parent has a
        #    left child and a right child (which may be another connector),
        #    producing a readable right-branch grouping.
        flat = []
        for c in children:
            if isinstance(c, list):
                for cc in c:
                    flat.append(cc)
            else:
                flat.append(c)

        if not flat:
            return

        if len(flat) == 1:
            self.emit_child_edge(parent_id, flat[0])
            return

        if len(flat) == 2:
            self.emit_child_edge(parent_id, flat[0])
            self.emit_child_edge(parent_id, flat[1])
            return

        def build_group_node(remaining: list) -> str:
            # Build a connector node representing the group of `remaining`
            conn = self.make_conn()
            self.emit_child_edge(conn, remaining[0])
            rest = remaining[1:]
            if len(rest) == 1:
                self.emit_child_edge(conn, rest[0])
            else:
                next_group = build_group_node(rest)
                self.lines.append(f'  {conn} -> {next_group};')
            return conn

        # attach first child directly as the left child
        self.emit_child_edge(parent_id, flat[0])
        remaining = flat[1:]
        if len(remaining) == 1:
            self.emit_child_edge(parent_id, remaining[0])
        else:
            group = build_group_node(remaining)
            self.lines.append(f'  {parent_id} -> {group};')

    def walk(self, n: Any) -> None:
        # Emit the DOT node for AST node `n` and recurse on its children.
        # The label uses `nodetype` and (optionally) `value` on a new line.
        this_id = self.nid(n)
        nodetype = getattr(n, 'nodetype', None)
        value = getattr(n, 'value', None)
        label = (nodetype if nodetype is not None else str(n)) + (f"\\n{self.escape(value)}" if value is not None else '')
        self.lines.append(f'  {this_id} [label="{label}"];')
        self.attach_children_binary(this_id, getattr(n, 'children', []))

    def to_dot(self, node: Any) -> str:
        # Public API: convert `node` (an AST-like object, a list of nodes, or
        # a scalar) into the DOT textual representation. Resets internal
        # counters so calling `to_dot` repeatedly produces fresh ids.
        self.lines = ['digraph AST {', '  node [shape=box];']
        self.counter = {'i': 0}
        self.ids = {}

        if self._is_ast_like(node):
            self.walk(node)
        elif isinstance(node, list):
            # create an artificial Program root for top-level lists
            root_id = self.new_id()
            self.lines.append(f'  {root_id} [label="Program"];')
            self.attach_children_binary(root_id, node)
        else:
            leaf_id = self.make_leaf(str(node))
            self.lines.append(f'  {leaf_id} [label="{self.escape(str(node))}"];')

        self.lines.append('}')
        return '\n'.join(self.lines)
