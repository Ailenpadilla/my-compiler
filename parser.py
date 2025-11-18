# parser.out -> se genera solo

# Se importan los tokens y el objeto lexer generado previamente en el lexer
from lexer import tokens, lexer as lexing
import ply.yacc as yacc  # analizador sintactico
from pathlib import Path
import shutil
import subprocess
from ast_exporter import ASTDotExporter
from ast_node import ASTNode
from semantic_context import SEM
from helpers import (
    new_temp,
    is_numeric,
    combine_numeric,
    ensure_assign_compatible,
)

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
    # root node for entire program; ignore init in the AST (semantic only)
    if len(p) == 3:
        prog_children = p[2] if isinstance(p[2], list) else [p[2]]
        p[0] = ASTNode('Program', children=prog_children)
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
    '''
    print(f'{p.slice[1].type} -> sentencia')
    p[0] = p[1]
    
    
def p_write(p):
    '''write : WRITE A_PARENTESIS CADENA C_PARENTESIS
    '''
    print(f'write ( CADENA ) -> write')
    node = ASTNode('WRITE', children=['write',p[3]], dtype=None)
    p[0] = node
    
    
def p_read(p):
    '''read : READ A_PARENTESIS VARIABLE C_PARENTESIS
    '''
    print(f'read ( VARIABLE ) -> read')
    try:
        lineno = p.lineno(3)
    except Exception:
        lineno = 0
    SEM.ensure_declared(p[3], lineno)
    node = ASTNode('READ', children=['read',p[3]], dtype=None)
    p[0] = node


def p_init(p):
    '''init : INIT A_LLAVE declaracion C_LLAVE
    '''
    # Process declarations semantically; do not build AST nodes for init
    p[0] = None
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
    # Create one Declaration node per variable so the tree has a clear
    # left/right structure: left = Type, right = Var (similar to WRITE/READ)
    # Semantic: register declarations and check duplicates
    try:
        lineno = p.lineno(1)
    except Exception:
        lineno = 0
    for n in names:
        SEM.set_decl(n, tipo, lineno)

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
                | VARIABLE ASIGNACION equal_expressions
    '''
    # Assignment: VARIABLE := expresion
    print(f'VARIABLE ASIGNACION {p.slice[3].type} -> asignacion')
    # Semantic checks
    try:
        lineno = p.lineno(1)
    except Exception:
        lineno = 0
    lhs_name = p[1]
    lhs_t = SEM.ensure_declared(lhs_name, lineno)
    rhs_node = p[3]
    # Special handling: expand equalExpressions into assignment + nested IF chain targeting the LHS
    if isinstance(rhs_node, ASTNode) and rhs_node.nodetype == 'EqualExpressions':
        if lhs_t != 'Bool':
            raise Exception(f"Error semántico (línea {lineno}): equalExpressions solo puede asignarse a variables Boolean")

        def build_equal_expr_chain(target_var, exprs):
            temps = []
            assigns_top = []
            for i, e in enumerate(exprs):
                tname = new_temp()
                temps.append(tname)
            # Assign first two expressions
            assigns_top.append(ASTNode(':=', children=[temps[0], exprs[0]]))
            assigns_top.append(ASTNode(':=', children=[temps[1], exprs[1]]))

            # Default else branch assigns false to target
            else_branch = ASTNode(':=', children=[target_var, ASTNode('false', dtype='Bool')])

            # Build nested IFs from the end for expr3..exprN
            n = len(exprs)
            for k in range(n, 2, -1):
                tk = temps[k-1]
                assign_k = ASTNode(':=', children=[tk, exprs[k-1]])
                comps = []
                for i in range(0, k-1):
                    comps.append(ASTNode('==', children=[tk, temps[i]], dtype='Bool'))
                cond = comps[0]
                for c in comps[1:]:
                    cond = ASTNode('or', children=[cond, c], dtype='Bool')
                then_true = ASTNode(':=', children=[target_var, ASTNode('true', dtype='Bool')])
                body = ASTNode('Body', children=[then_true, else_branch])
                if_node = ASTNode('IF', children=[cond, body])
                else_branch = ASTNode('Block', children=[assign_k, if_node])

            # Top IF compares first two temps
            cond12 = ASTNode('==', children=[temps[0], temps[1]], dtype='Bool')
            then_true = ASTNode(':=', children=[target_var, ASTNode('true', dtype='Bool')])
            top_body = ASTNode('Body', children=[then_true, else_branch])
            top_if = ASTNode('IF', children=[cond12, top_body])
            return ASTNode('EqualExpressions', children=assigns_top + [top_if], dtype='Bool')

        # rhs_node.children contains the original expressions list
        exprs = rhs_node.children if isinstance(rhs_node.children, list) else [rhs_node.children]
        node = build_equal_expr_chain(p[1], exprs)
    else:
        rhs_t = getattr(rhs_node, 'dtype', None)
        if rhs_t is None:
            rhs_t = 'Unknown'
        ensure_assign_compatible(lhs_t, rhs_t, lineno, lhs_name)
        node = ASTNode(':=', children=[p[1],p[3]], dtype=lhs_t)
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

    # Validate condition type is boolean
    cond = p[3]
    if getattr(cond, 'dtype', None) != 'Bool':
        try:
            lineno = p.lineno(1)
        except Exception:
            lineno = 0
        raise Exception(f"Error semántico (línea {lineno}): la condición de while debe ser booleana")

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
        # Semantic: condition must be boolean
        if getattr(p[3], 'dtype', None) != 'Bool':
            try:
                lineno = p.lineno(1)
            except Exception:
                lineno = 0
            raise Exception(f"Error semántico (línea {lineno}): la condición de if debe ser booleana")
        then_children = wrap_block(p[6])
        node = ASTNode('IF', children=[p[3]] + then_children)
    else:
        print(f'if ( condicion ) {{ programa }} else {{ programa }} -> if_else')
        # Build then and else subtrees. If they contain multiple statements,
        # keep them wrapped in a Block so we can attach them as left/right of Body.
        if getattr(p[3], 'dtype', None) != 'Bool':
            try:
                lineno = p.lineno(1)
            except Exception:
                lineno = 0
            raise Exception(f"Error semántico (línea {lineno}): la condición de if debe ser booleana")
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
                    | VARIABLE
                    | NOT VARIABLE
                    | VARIABLE AND VARIABLE
                    | VARIABLE OR VARIABLE
    '''
    if len(p) == 4:
        # If both operands are variables, ensure they are boolean variables and
        # normalize each to a comparator: var == true
        if p.slice[1].type == 'VARIABLE' and p.slice[3].type == 'VARIABLE':
            try:
                lineno = p.lineno(1)
            except Exception:
                lineno = 0
            t1 = SEM.ensure_declared(p[1], lineno)
            t2 = SEM.ensure_declared(p[3], lineno)
            if t1 != 'Bool' or t2 != 'Bool':
                raise Exception(f"Error semántico (línea {lineno}): operadores lógicos requieren variables booleanas")
            v1 = ASTNode(p[1], dtype='Bool')
            v2 = ASTNode(p[3], dtype='Bool')
            # Create distinct literal leaves so each comparator has its own
            lit_true_left = ASTNode('true', dtype='Bool')
            lit_true_right = ASTNode('true', dtype='Bool')
            left_cmp = ASTNode('==', children=[v1, lit_true_left], dtype='Bool')
            right_cmp = ASTNode('==', children=[v2, lit_true_right], dtype='Bool')
            node = ASTNode(p[2], children=[left_cmp, right_cmp], dtype='Bool')
            p[0] = node
            return
        print(f'comparacion {p.slice[2].type} comparacion -> condicion')
        t1 = getattr(p[1], 'dtype', None)
        t2 = getattr(p[3], 'dtype', None)
        if t1 != 'Bool' or t2 != 'Bool':
            try:
                lineno = p.lineno(2)
            except Exception:
                lineno = 0
            raise Exception(f"Error semántico (línea {lineno}): operadores lógicos requieren operandos booleanos")
        node = ASTNode(p[2], children=[p[1], p[3]], dtype='Bool')
    elif len(p) == 3:
        # NOT of comparison or NOT of boolean variable
        if p.slice[2].type == 'VARIABLE':
            try:
                lineno = p.lineno(2)
            except Exception:
                lineno = 0
            vname = p[2]
            vtype = SEM.ensure_declared(vname, lineno)
            if vtype != 'Bool':
                raise Exception(f"Error semántico (línea {lineno}): 'not' requiere una variable booleana")
            # Normalize to comparison: v == false
            left = ASTNode(vname, dtype='Bool')
            right = ASTNode('false', dtype='Bool')
            node = ASTNode('==', children=[left, right], dtype='Bool')
            p[0] = node
            return
        print(f'NOT comparacion -> condicion')
        comp = p[2]
        if isinstance(comp, ASTNode) and comp.nodetype in diccionarioComparadoresNot and len(comp.children) == 2:
            inverted = diccionarioComparadoresNot[comp.nodetype]
            node = ASTNode(inverted, children=[comp.children[0], comp.children[1]], dtype='Bool')
        else:
            if getattr(p[2], 'dtype', None) != 'Bool':
                try:
                    lineno = p.lineno(1)
                except Exception:
                    lineno = 0
                raise Exception(f"Error semántico (línea {lineno}): 'not' requiere una expresión booleana")
            node = ASTNode('CondNot', children=[p[2]], dtype='Bool')
    else:
        # Single comparison result or a boolean variable
        if p.slice[1].type == 'VARIABLE':
            print(f'bool -> condicion')
            try:
                lineno = p.lineno(1)
            except Exception:
                lineno = 0
            vname = p[1]
            vtype = SEM.ensure_declared(vname, lineno)
            if vtype != 'Bool':
                raise Exception(f"Error semántico (línea {lineno}): la condición debe ser una variable booleana")
            # Normalize to comparison: v == true
            left = ASTNode(vname, dtype='Bool')
            right = ASTNode('true', dtype='Bool')
            node = ASTNode('==', children=[left, right], dtype='Bool')
        else:
            print(f'comparacion -> condicion')
            node = p[1]
            if getattr(node, 'dtype', None) != 'Bool':
                try:
                    lineno = getattr(p, 'lineno', lambda i: 0)(1)
                except Exception:
                    lineno = 0
                raise Exception(f"Error semántico (línea {lineno}): la condición debe ser booleana")
    p[0] = node

def p_comparacion(p):
    '''comparacion : expresion COMPARADOR expresion
    '''
    print(f'expresion COMPARADOR expresion -> comparacion')
    left = p[1]
    right = p[3]
    op = p[2]
    t1 = getattr(left, 'dtype', None)
    t2 = getattr(right, 'dtype', None)
    try:
        lineno = p.lineno(2)
    except Exception:
        lineno = 0
    if op in ('<', '<=', '>', '>='):
        if not (is_numeric(t1) and is_numeric(t2)):
            raise Exception(f"Error semántico (línea {lineno}): comparadores relacionales requieren operandos numéricos, recibió {t1} y {t2}")
    else:
        if not (t1 == t2 or (is_numeric(t1) and is_numeric(t2))):
            raise Exception(f"Error semántico (línea {lineno}): comparación entre tipos incompatibles {t1} y {t2}")
    node = ASTNode(op, children=[left, right], dtype='Bool')
    p[0] = node


def p_equal_expressions(p):
    '''equal_expressions : EQUAL_EXPRESSIONS A_PARENTESIS list_expressions C_PARENTESIS
    '''
    print(f'equalExpressions ( list_expressions ) -> equal_expressions')
    exprs = p[3] if isinstance(p[3], list) else [p[3]]

    # Semantic: require all expressions to be same type (or all numeric)
    types = [getattr(e, 'dtype', None) for e in exprs]
    try:
        lineno = p.lineno(1)
    except Exception:
        lineno = 0
    if types:
        base = types[0]
        for t in types[1:]:
            if not (t == base or (is_numeric(t) and is_numeric(base))):
                raise Exception(f"Error semántico (línea {lineno}): equalExpressions con tipos incompatibles {base} y {t}")

    # Carry the raw expressions; p_asignacion expands this into assignments
    # and nested IFs that assign to the LHS boolean variable.
    node = ASTNode('EqualExpressions', children=exprs, dtype='Bool')
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
    # Build an arithmetic AST equivalent to: (anio * 10000) + (mes * 100) + dia
    # This follows the project's convention of representing expressions as
    # ASTNodes with operators '+', '*', etc., so the code generator can lower
    # the arithmetic like any other expression.
    raw = p[3]
    try:
        dia, mes, anio = map(int, raw.split('-'))
        # Basic validation (lexer already enforces general shape and ranges)
        mdays = [0,31,29,31,30,31,30,31,31,30,31,30,31]
        if not (1 <= mes <= 12 and 1 <= dia <= mdays[mes]):
            raise ValueError(f"Fecha inválida '{raw}'")
        if mes == 2 and dia == 29:
            is_leap = (anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0))
            if not is_leap:
                raise ValueError(f"Fecha inválida (no es año bisiesto) '{raw}'")

        # Create numeric AST nodes for year, month, day and the constants
        node_year = ASTNode(str(anio), dtype='Int')
        node_month = ASTNode(str(mes), dtype='Int')
        node_day = ASTNode(str(dia), dtype='Int')
        node_10000 = ASTNode(str(10000), dtype='Int')
        node_100 = ASTNode(str(100), dtype='Int')

        # anio * 10000
        mul_year = ASTNode('*', children=[node_year, node_10000], dtype='Int')
        # mes * 100
        mul_month = ASTNode('*', children=[node_month, node_100], dtype='Int')
        # (mes * 100) + dia
        add_month_day = ASTNode('+', children=[mul_month, node_day], dtype='Int')
        # (anio * 10000) + ((mes * 100) + dia)
        total = ASTNode('+', children=[mul_year, add_month_day], dtype='DateConverted')
        p[0] = total
    except Exception as e:
        # On failure, fall back to a ConvDate node so later stages can
        # implement runtime conversion or raise an error.
        print('Warning: convDate -> building arithmetic AST failed:', e)
        node = ASTNode('ConvDate', value=raw, dtype='DateConverted')
        p[0] = node


def p_expresion_menos(p):
    'expresion : expresion MENOS termino'
    print('expresion - termino -> expresion')
    try:
        lineno = p.lineno(2)
    except Exception:
        lineno = 0
    t = combine_numeric(getattr(p[1], 'dtype', None), getattr(p[3], 'dtype', None), lineno, '-')
    node = ASTNode('-', children=[p[1], p[3]], dtype=t)
    p[0] = node
    
    
def p_expresion_mas(p):
    'expresion : expresion MAS termino'
    print('expresion + termino -> expresion')
    try:
        lineno = p.lineno(2)
    except Exception:
        lineno = 0
    t = combine_numeric(getattr(p[1], 'dtype', None), getattr(p[3], 'dtype', None), lineno, '+')
    node = ASTNode('+', children=[p[1], p[3]], dtype=t)
    p[0] = node


def p_expresion_termino(p):
    'expresion : termino'
    print('termino -> expresion')
    p[0] = p[1]


def p_termino_multiplicacion(p):
    'termino : termino MULTIPLICACION elemento'
    print('termino * elemento -> termino')
    try:
        lineno = p.lineno(2)
    except Exception:
        lineno = 0
    t = combine_numeric(getattr(p[1], 'dtype', None), getattr(p[3], 'dtype', None), lineno, '*')
    node = ASTNode('*', children=[p[1], p[3]], dtype=t)
    p[0] = node


def p_termino_division(p):
    'termino : termino DIVISION elemento'
    print('termino / elemento -> termino')
    try:
        lineno = p.lineno(2)
    except Exception:
        lineno = 0
    t = combine_numeric(getattr(p[1], 'dtype', None), getattr(p[3], 'dtype', None), lineno, '/')
    t = 'Float' if t in ('Int', 'Float') else t
    node = ASTNode('/', children=[p[1], p[3]], dtype=t)
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
    try:
        lineno = p.lineno(1)
    except Exception:
        lineno = 0
    if tok == 'VARIABLE':
        vname = p[1]
        vtype = SEM.ensure_declared(vname, lineno)
        node = ASTNode(vname, dtype=vtype)
    elif tok == 'N_ENTERO':
        node = ASTNode(str(p[1]), dtype='Int')
    elif tok == 'N_FLOAT':
        node = ASTNode(str(p[1]), dtype='Float')
    elif tok == 'CADENA':
        node = ASTNode(str(p[1]), dtype='String')
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
                | BOOLEAN
    '''
    print(f'{p.slice[1].type} -> tipo_dato')
    # return a simple string representing type
    if p.slice[1].type == 'FLOAT':
        p[0] = 'Float'
    elif p.slice[1].type == 'INT':
        p[0] = 'Int'
    elif p.slice[1].type == 'STRING':
        p[0] = 'String'
    elif p.slice[1].type == 'DATE_CONVERTED':
        p[0] = 'DateConverted'
    else:  # BOOLEAN
        p[0] = 'Bool'


# Error rule for syntax errors
def p_error(p):
    raise Exception(f"Error en la linea {p.lineno or ''} at {p.value or ''}")


def ejecutar_parser(code):
    # Build the parser
    parser = yacc.yacc()

    # Ensure lexer line numbers reset and parse using the lexer object so
    # tokens come from the lexical analyzer implementation in lexer.py
    try:
        lexing.lineno = 1
        print('Resetting lexer line number to 1')
    except Exception:
        print('Warning: lexer has no lineno attribute to reset')
        pass
    
    # Load symbols from lexer-generated table before parsing (semantic checks)
    try:
        SEM.load_from_table(Path('./resources/tabla_simbolos.txt'))
    except Exception as e:
        print('Warning: no se pudo cargar tabla de símbolos:', e)

    # Ensure we provide the same lexer instance to the parser so tokens
    # come from `lexer.py`. PLY will call lexing.input(code) internally.
    ast = parser.parse(code, lexer=lexing)

    # Write DOT representation of the AST
    try:
        dot_path = Path('./intermediate-code.dot')
        dot_text = ASTDotExporter().to_dot(ast)
        dot_path.write_text(dot_text, encoding='utf-8')
        print(f'Wrote AST DOT to {dot_path.resolve()}')

        # If dot (Graphviz) is available, try to create a PNG
        if shutil.which('dot'):
            png_path = Path('./intermediate-code.png')
            subprocess.run([shutil.which('dot'), '-Tpng', str(dot_path), '-o', str(png_path)])
            if png_path.exists():
                print(f'Wrote AST PNG to {png_path.resolve()}')
    except Exception as e:
        print('Error while writing DOT/PNG:', e)
