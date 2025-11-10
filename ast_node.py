class ASTNode:
    def __init__(self, nodetype, value=None, children=None, dtype=None):
        self.nodetype = nodetype
        self.value = value
        self.children = children or []
        self.dtype = dtype

    def to_lines(self, level=0):
        indent = '  ' * level
        val = f": {self.value}" if self.value is not None else ""
        lines = [f"{indent}{self.nodetype}{val}"]
        for c in self.children:
            if isinstance(c, ASTNode):
                lines.extend(c.to_lines(level + 1))
            else:
                lines.append('  ' * (level + 1) + str(c))
        return lines

    def to_string(self):
        return '\n'.join(self.to_lines())

