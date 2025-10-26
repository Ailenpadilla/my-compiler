# parser.out -> se genera solo

# Se importan los tokens generado previamente en el lexer
from lexer import tokens
import ply.yacc as yacc  # analizador sintactico
from pathlib import Path
import shutil
import subprocess
from graphviz import Source


# --- AST node and symbol table helpers ---
class ASTNode:
    def __init__(self, nodetype, value=None, children=None):
        self.nodetype = nodetype
        self.value = value
        self.children = children or []

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


symbol_table = []

def add_symbol(name, tipo='', valor=''):
    # avoid duplicates for declared variables
    for e in symbol_table:
        if e['nombre'] == name and (tipo == '' or e.get('tipo') == tipo):
            return
    symbol_table.append({'nombre': name, 'tipo': tipo, 'valor': valor})

def collect_var_names(lista):
    # lista is either [name] or [name, ...]
    names = []
    if isinstance(lista, list):
        for n in lista:
            names.append(n)
    else:
        names.append(lista)
    return names

diccionarioComparadores = {
    ">=":   "BLT",
    ">":   "BLE",
    "<=":   "BGT",
    "<":   "BGE",
    "<>":   "BEQ",
    "==":   "BNE"
}

diccionarioComparadoresNot = {
    ">=":   "<",
    ">":   "<=",
    "<=":   ">",
    "<":   ">=",
    "<>":   "==",
    "==":   "<>"
}


precedence = (
    ('right', 'ASIGNACION'),
    ('right', 'MENOS'),
    ('left', 'MULTIPLICACION', 'DIVISION'),
    ('left', 'A_PARENTESIS', 'C_PARENTESIS'),
)


def p_start(p):
    '''start : init programa
            | programa 
    '''
    # root node for entire program
    # If init is present (start : init programa), combine the Init node
    # with the programa statements. Otherwise, build Program from programa.
    if len(p) == 3:
        # p[1] is Init (ASTNode), p[2] is programa (list or single node)
        prog_children = p[2] if isinstance(p[2], list) else [p[2]]
        p[0] = ASTNode('Program', children=[p[1]] + prog_children)
    else:
        p[0] = ASTNode('Program', children=p[1] if isinstance(p[1], list) else [p[1]])
    print('FIN')


def p_programa(p):
    '''programa : programa sentencia
                | sentencia
    '''
    if len(p) == 3:
        # append statement to program list
        if isinstance(p[1], list):
            p[0] = p[1] + [p[2]]
        else:
            p[0] = [p[1], p[2]]
        print(f'programa sentencia -> programa')
    else:
        p[0] = [p[1]]
        print(f'sentencia -> programa')


def p_sentencia(p):
    '''sentencia : asignacion
                | while
                | if_else
                | write
                | read
                | equal_expressions
    '''
    print(f'{p.slice[1].type} -> sentencia')
    p[0] = p[1]
    
    
def p_write(p):
    '''write : WRITE A_PARENTESIS CADENA C_PARENTESIS
    '''
    print(f'write ( CADENA ) -> write')
    node = ASTNode('WRITE', children=['write',p[3]])
    p[0] = node
    
    
def p_read(p):
    '''read : READ A_PARENTESIS VARIABLE C_PARENTESIS
    '''
    print(f'read ( VARIABLE ) -> read')
    add_symbol(p[3], '')
    node = ASTNode('READ', children=['read',p[3]])
    p[0] = node


def p_init(p):
    '''init : INIT A_LLAVE declaracion C_LLAVE
    '''
    # declaracion returns list of declaration nodes
    node = ASTNode('Init', children=p[3] if isinstance(p[3], list) else [p[3]])
    p[0] = node
    print(f'init {{ declaracion }} -> init')


def p_declaracion(p):
    '''declaracion : declaracion linea_declaracion
                    | linea_declaracion
    '''
    if len(p) == 3:
        if isinstance(p[1], list):
            p[0] = p[1] + [p[2]]
        else:
            p[0] = [p[1], p[2]]
        print(f'declaracion linea_declaracion -> declaracion')
    else:
        p[0] = [p[1]]
        print(f'linea_declaracion -> declaracion')
    

def p_linea_declaracion(p):
    '''linea_declaracion : lista_variables ASIGNACION_TIPO tipo_dato
    '''
    # lista_variables returns either a VARIABLE or list
    varlist = p[1]
    tipo = p[3]
    names = []
    if isinstance(varlist, list):
        names = varlist
    else:
        names = [varlist]
    # add to symbol table
    for n in names:
        add_symbol(n, tipo, '')
    # Create one Declaration node per variable so the tree has a clear
    # left/right structure: left = Type, right = Var (similar to WRITE/READ)
    decl_nodes = [ASTNode('Declaration', children=[ASTNode('Type', value=tipo), ASTNode('Var', value=n)]) for n in names]
    # If only one variable was declared on the line, return a single node,
    # otherwise return the list so higher-level rules can flatten them.
    if len(decl_nodes) == 1:
        p[0] = decl_nodes[0]
    else:
        p[0] = decl_nodes
    print(f'lista_variables ASIGNACION_TIPO tipo_dato -> linea_declaracion')


def p_asignacion(p):
    '''asignacion : VARIABLE ASIGNACION expresion
                | VARIABLE ASIGNACION conv_date
    '''
    # Assignment: VARIABLE := expresion
    print(f'VARIABLE ASIGNACION {p.slice[3].type} -> asignacion')
    add_symbol(p[1], '')
    node = ASTNode(':=', children=[p[1],p[3]])
    p[0] = node


def p_while(p):
    '''while : WHILE A_PARENTESIS condicion C_PARENTESIS A_LLAVE programa C_LLAVE
    '''
    # If the block (p[6]) is a single statement, attach it directly to While.
    # If it's multiple statements, keep a Block node as the body.
    def wrap_block(block):
        if isinstance(block, list):
            return block
        else:
            return [block]

    body_children = wrap_block(p[6])
    if len(body_children) == 1:
        node = ASTNode('While', children=[p[3], body_children[0]])
    else:
        node = ASTNode('While', children=[p[3], ASTNode('Block', children=body_children)])
    p[0] = node
    print(f'while ( condicion ) {{ programa }} -> while')
    
    
def p_if_else(p):
    '''if_else : IF A_PARENTESIS condicion C_PARENTESIS A_LLAVE programa C_LLAVE
                | IF A_PARENTESIS condicion C_PARENTESIS A_LLAVE programa C_LLAVE ELSE A_LLAVE programa C_LLAVE
    '''
    # If the block (p[6] or p[10]) is a single statement, attach it directly
    # If it's multiple statements (a list with length>1), wrap them in a Then/Else node
    def wrap_block(block):
        # block may be a single ASTNode or a list of ASTNodes
        # Return a list of ASTNode children for the given block.
        # If block is already a list, return it; otherwise wrap single node in a list.
        if isinstance(block, list):
            return block
        else:
            return [block]

    if len(p) == 8:
        print(f'if ( condicion ) {{ programa }} -> if_else')
        # flatten block statements into IF's children: [cond, stmt1, stmt2, ...]
        then_children = wrap_block(p[6])
        node = ASTNode('IF', children=[p[3]] + then_children)
    else:
        print(f'if ( condicion ) {{ programa }} else {{ programa }} -> if_else')
        # Build then and else subtrees. If they contain multiple statements,
        # keep them wrapped in a Block so we can attach them as left/right of Body.
        then_children = wrap_block(p[6])
        else_children = wrap_block(p[10])

        def make_side(children_list):
            if len(children_list) == 1:
                return children_list[0]
            else:
                return ASTNode('Block', children=children_list)

        then_node = make_side(then_children)
        else_node = make_side(else_children)

        body = ASTNode('Body', children=[then_node, else_node])
        node = ASTNode('IF', children=[p[3], body])
    p[0] = node


def p_condicion(p):
    '''condicion : comparacion AND comparacion
                    | comparacion OR comparacion
                    | NOT comparacion
                    | comparacion
    '''
    if len(p) == 4:
        print(f'comparacion {p.slice[2].type} comparacion -> condicion')
        node = ASTNode(p[2], children=[p[1], p[3]])
    elif len(p) == 3:
        # Try to invert a simple comparison by swapping the comparator
        # using diccionarioComparadoresNot. If p[2] is not a comparacion
        # node with two children or its nodetype isn't in the dictionary,
        # fall back to producing a CondNot node.
        print(f'NOT comparacion -> condicion')
        comp = p[2]
        if isinstance(comp, ASTNode) and comp.nodetype in diccionarioComparadoresNot and len(comp.children) == 2:
            inverted = diccionarioComparadoresNot[comp.nodetype]
            node = ASTNode(inverted, children=[comp.children[0], comp.children[1]])
        else:
            node = ASTNode('CondNot', children=[p[2]])
    else:
        print(f'comparacion -> condicion')
        node = p[1]
    p[0] = node

def p_comparacion(p):
    'comparacion : expresion COMPARADOR expresion'
    print(f'expresion COMPARADOR expresion -> comparacion')
    node = ASTNode(p[2], children=[p[1], p[3]])
    p[0] = node


def p_equal_expressions(p):
    '''equal_expressions : EQUAL_EXPRESSIONS A_PARENTESIS list_expressions C_PARENTESIS
    '''
    print(f'equalExpressions ( list_expressions ) -> equal_expressions')
    node = ASTNode('EqualExpressions', children=p[3] if isinstance(p[3], list) else [p[3]])
    p[0] = node
    

def p_list_expressions(p):
    '''list_expressions : expresion SEPARADOR_VARIABLES list_expressions
                        | expresion
    '''
    if len(p) == 4:
        # p[1] is expresion, p[3] is list
        if isinstance(p[3], list):
            p[0] = [p[1]] + p[3]
        else:
            p[0] = [p[1], p[3]]
        print(f'expresion , list_expressions -> list_expressions')
    else:
        p[0] = [p[1]]
        print(f'expresion -> list_expressions')


def p_conv_date(p):
    '''conv_date : CONV_DATE A_PARENTESIS DATE C_PARENTESIS
    '''
    print(f'convDate ( DATE ) -> conv_date')
    node = ASTNode('ConvDate', value=p[3])
    p[0] = node


def p_expresion_menos(p):
    'expresion : expresion MENOS termino'
    print('expresion - termino -> expresion')
    node = ASTNode('-', children=[p[1], p[3]])
    p[0] = node
    
    
def p_expresion_mas(p):
    'expresion : expresion MAS termino'
    print('expresion + termino -> expresion')
    node = ASTNode('+', children=[p[1], p[3]])
    p[0] = node


def p_expresion_termino(p):
    'expresion : termino'
    print('termino -> expresion')
    p[0] = p[1]


def p_termino_multiplicacion(p):
    'termino : termino MULTIPLICACION elemento'
    print('termino * elemento -> termino')
    node = ASTNode('*', children=[p[1], p[3]])
    p[0] = node


def p_termino_division(p):
    'termino : termino DIVISION elemento'
    print('termino / elemento -> termino')
    node = ASTNode('/', children=[p[1], p[3]])
    p[0] = node


def p_termino_elemento(p):
    'termino : elemento'
    print('elemento -> termino')
    p[0] = p[1]


def p_elemento_expresion(p):
    'elemento : A_PARENTESIS expresion C_PARENTESIS'
    print('( expresion ) -> elemento')
    p[0] = p[2]


def p_elemento(p):
    '''elemento : N_ENTERO
                | VARIABLE
                | N_FLOAT
                | CADENA
    '''
    print(f'{p.slice[1].type} -> elemento') 
    tok = p.slice[1].type
    if tok == 'VARIABLE':
        add_symbol(p[1], '')
        node = ASTNode(p[1])
    else:
        node = ASTNode(str(p[1]))
    p[0] = node
    
    
def p_lista_variables(p):
    '''lista_variables : VARIABLE SEPARADOR_VARIABLES lista_variables
                       | VARIABLE
    '''
    if len(p) == 4:
        # p[3] may be list
        if isinstance(p[3], list):
            p[0] = [p[1]] + p[3]
        else:
            p[0] = [p[1], p[3]]
        print(f'VARIABLE , lista_variables -> lista_variables')
    else:
        p[0] = p[1]
        print(f'VARIABLE -> lista_variables')
    

def p_tipo_dato(p):
    '''tipo_dato : FLOAT
                | INT
                | STRING
                | DATE_CONVERTED
    '''
    print(f'{p.slice[1].type} -> tipo_dato')
    # return a simple string representing type
    if p.slice[1].type == 'FLOAT':
        p[0] = 'Float'
    elif p.slice[1].type == 'INT':
        p[0] = 'Int'
    else:
        p[0] = 'String'


# Error rule for syntax errors
def p_error(p):
    raise Exception(f"Error en la linea {p.lineno or ''} at {p.value or ''}")


def ejecutar_parser():
    # Build the parser
    parser = yacc.yacc()
    # input file preference: ./prueba.txt, then resources/parser_test.txt
    possible = [Path('./prueba.txt'), Path('./resources/parser_test.txt')]
    path_parser = next((p for p in possible if p.exists()), possible[-1])
    code = path_parser.read_text()
    # reset symbol table
    global symbol_table
    symbol_table = []
    ast = parser.parse(code)

    # write intermediate code as AST tree to intermediate-code.txt
    out_path = Path('./intermediate-code.txt')
    if isinstance(ast, ASTNode):
        out_text = ast.to_string()
    else:
        # sometimes parser returns list
        if isinstance(ast, list):
            lines = []
            for n in ast:
                if isinstance(n, ASTNode):
                    lines.extend(n.to_lines())
                else:
                    lines.append(str(n))
            out_text = '\n'.join(lines)
        else:
            out_text = str(ast)

    out_path.write_text(out_text, encoding='utf-8')

    # write symbol table to resources/tabla_simbolos.txt
    # output_path = Path('./resources/tabla_simbolos.txt')
    # with output_path.open('w', encoding='utf-8') as f:
    #     f.write(f"{'Nombre':<20}{'Tipo de Dato':<15}{'Valor':<30}\n")
    #     f.write('-' * 65 + '\n')
    #     for entry in symbol_table:
    #         f.write(f"{entry['nombre']:<20}{entry['tipo']:<15}{str(entry['valor']):<30}\n")

    # print(f'Wrote intermediate code to {out_path.resolve()}')
    # print(f'Wrote symbol table to {output_path.resolve()}') 

    # Also write DOT representation of the AST
    try:
        dot_path = Path('./intermediate-code.dot')
        def ast_to_dot(node):
            # produce DOT lines with binaryized children via connector nodes
            lines = ['digraph AST {', '  node [shape=box];']
            counter = {'i': 0}
            ids = {}

            def nid(obj):
                # unique id for ASTNode objects
                if id(obj) in ids:
                    return ids[id(obj)]
                counter['i'] += 1
                ids[id(obj)] = f'n{counter["i"]}'
                return ids[id(obj)]

            def new_id():
                counter['i'] += 1
                return f'n{counter["i"]}'

            def escape(s):
                return str(s).replace('"', '\\"')

            def make_leaf(label):
                lid = new_id()
                lines.append(f'  {lid} [label="{escape(label)}"];')
                return lid

            def make_conn():
                cid = new_id()
                # connector node; visually distinct
                lines.append(f'  {cid} [label="·", style="dashed"];')
                return cid

            def emit_child_edge(parent_id, child):
                if isinstance(child, ASTNode):
                    cid = nid(child)
                    lines.append(f'  {parent_id} -> {cid};')
                    walk(child)
                else:
                    leaf_id = make_leaf(child)
                    lines.append(f'  {parent_id} -> {leaf_id};')

            def attach_children_binary(parent_id, children):
                # Flatten one level of nested lists so we don't produce Python list
                # string representations in the DOT file (these came from
                # production rules returning lists of nodes).
                flat = []
                for c in children:
                    if isinstance(c, list):
                        for cc in c:
                            flat.append(cc)
                    else:
                        flat.append(c)

                # If node is a leaf (no children), do not add dummy nodes.
                if not flat:
                    return

                # If exactly one child, attach it and return (no dummy right child)
                if len(flat) == 1:
                    emit_child_edge(parent_id, flat[0])
                    return

                # If exactly two children, attach both directly (no connector)
                if len(flat) == 2:
                    emit_child_edge(parent_id, flat[0])
                    emit_child_edge(parent_id, flat[1])
                    return

                # Helper to build a connector group for 2+ elements
                def build_group_node(remaining):
                    # remaining has length >= 2 here
                    conn = make_conn()
                    # left = first element
                    emit_child_edge(conn, remaining[0])
                    # right = if more than one left, either a nested group or direct child
                    rest = remaining[1:]
                    if len(rest) == 1:
                        # attach single remaining element directly
                        emit_child_edge(conn, rest[0])
                    else:
                        # build nested group for remaining elements
                        next_group = build_group_node(rest)
                        lines.append(f'  {conn} -> {next_group};')
                    return conn

                # Left child for parent: attach first child
                emit_child_edge(parent_id, flat[0])

                # Right child for parent: if there's exactly one remaining child, attach it directly,
                # otherwise build a connector group (only if there are 2+ remaining items)
                remaining = flat[1:]
                if len(remaining) == 1:
                    emit_child_edge(parent_id, remaining[0])
                else:
                    # remaining has length >= 2 -> need a group connector
                    group = build_group_node(remaining)
                    lines.append(f'  {parent_id} -> {group};')

            def walk(n):
                this_id = nid(n)
                label = n.nodetype + (f"\\n{escape(n.value)}" if n.value is not None else '')
                lines.append(f'  {this_id} [label="{label}"];')
                # binaryize children here
                attach_children_binary(this_id, n.children)

            if isinstance(node, ASTNode):
                walk(node)
            elif isinstance(node, list):
                # create artificial root
                root_id = new_id()
                lines.append(f'  {root_id} [label="Program"];')
                # attach program elements as binary under root
                attach_children_binary(root_id, node)
            else:
                # fallback single node
                leaf_id = make_leaf(str(node))
                lines.append(f'  {leaf_id} [label="{escape(str(node))}"];')

            lines.append('}')
            return '\n'.join(lines)

        dot_text = ast_to_dot(ast)
        dot_path.write_text(dot_text, encoding='utf-8')
        print(f'Wrote AST DOT to {dot_path.resolve()}')
        
        
        # Load your .dot file
        src = Source.from_file("intermediate-code.dot")

        # Render as PNG
        src.render("mygraph", format="png", cleanup=True)

        # If dot (Graphviz) is available, try to create a PNG
        if shutil.which('dot'):
            png_path = Path('./intermediate-code.png')
            subprocess.run([shutil.which('dot'), '-Tpng', str(dot_path), '-o', str(png_path)])
            if png_path.exists():
                print(f'Wrote AST PNG to {png_path.resolve()}')
    except Exception as e:
        print('Error while writing DOT/PNG:', e)
