# parser.out -> se genera solo

# Se importan los tokens generado previamente en el lexer
from lexer import tokens
import ply.yacc as yacc  # analizador sintactico
from pathlib import Path

diccionarioComparadores = {
    ">=":   "BLT",
    ">":   "BLE",
    "<=":   "BGT",
    "<":   "BGE",
    "<>":   "BEQ",
    "==":   "BNE"
}

diccionarioComparadoresNot = {
    ">=":   "BGE",
    ">":   "BGT",
    "<=":   "BLE",
    "<":   "BLT",
    "<>":   "BNE",
    "==":   "BEQ"
}


precedence = (
    ('right', 'ASIGNACION'),
    ('right', 'MENOS'),
    ('left', 'MULTIPLICACION', 'DIVISION'),
    ('left', 'A_PARENTESIS', 'C_PARENTESIS'),
)


def p_start(p):
    '''start : programa'''
    print('FIN')


def p_programa(p):
    '''programa : programa sentencia
                | sentencia
    '''
    if len(p) == 3:
        print(f'programa sentencia -> programa')
    else:
        print(f'sentencia -> programa')


def p_sentencia(p):
    '''sentencia : asignacion
                | while
                | if_else
                | init
                | write
                | read
                | equal_expressions
                | conv_date
    '''
    print(f'{p.slice[1].type} -> sentencia')
    
    
def p_write(p):
    '''write : WRITE A_PARENTESIS CADENA C_PARENTESIS
    '''
    print(f'WRITE ( {p.slice[3].type} ) -> sentencia')
    
    
def p_read(p):
    '''read : READ A_PARENTESIS VARIABLE C_PARENTESIS
    '''
    print(f'READ ( VARIABLE ) -> sentencia')


def p_init(p):
    '''init : INIT A_LLAVE declaracion C_LLAVE
    '''
    print(f'INIT {{ {p.slice[3].type} }} -> init')


def p_declaracion(p):
    '''declaracion : declaracion linea_declaracion
                    | linea_declaracion
    '''
    print(f'{p.slice[1].type} -> declaracion')
    

def p_linea_declaracion(p):
    '''linea_declaracion : lista_variables ASIGNACION_TIPO tipo_dato
    '''
    print(f'lista_variables ASIGNACION_TIPO tipo_dato -> linea_declaracion')


def p_asignacion(p):
    '''asignacion : VARIABLE ASIGNACION expresion
    '''
    print(f'VARIABLE ASIGNACION {p.slice[3].type} -> asignacion')


def p_while(p):
    '''while : WHILE A_PARENTESIS condicion C_PARENTESIS A_LLAVE programa C_LLAVE
    '''
    print(f'WHILE ( condicion ) {{ programa }} -> while')
    
    
def p_if_else(p):
    '''if_else : IF A_PARENTESIS condicion C_PARENTESIS A_LLAVE programa C_LLAVE
                | IF A_PARENTESIS condicion C_PARENTESIS A_LLAVE programa C_LLAVE ELSE A_LLAVE programa C_LLAVE
    '''
    print(f'IF ( condicion ) {{ programa }} ELSE {{ programa }} -> if_else')


def p_condicion(p):
    '''condicion : comparacion AND comparacion
                    | comparacion OR comparacion
                    | NOT comparacion
                    | comparacion
    '''
    print(f'{p.slice[1].type} -> condicion')
    

def p_comparacion(p):
    'comparacion : expresion COMPARADOR expresion'
    print(f'expresion COMPARADOR expresion -> comparacion')


def p_equal_expressions(p):
    '''equal_expressions : EQUAL_EXPRESSIONS A_PARENTESIS list_expressions C_PARENTESIS
    '''
    print(f'expresion EQUAL_EXPRESSIONS expresion -> equal_expressions')
    

def p_list_expressions(p):
    '''list_expressions : expresion SEPARADOR_VARIABLES list_expressions
                        | expresion
    '''
    print(f'{p.slice[1].type} -> list_expressions')
    

def p_conv_date(p):
    '''conv_date : CONV_DATE A_PARENTESIS DATE C_PARENTESIS
    '''
    print(f'CONV_DATE ( DATE ) -> conv_date')


def p_expresion_menos(p):
    'expresion : expresion MENOS termino'
    print('expresion - termino -> expresion')
    
    
def p_expresion_mas(p):
    'expresion : expresion MAS termino'
    print('expresion + termino -> expresion')


def p_expresion_termino(p):
    'expresion : termino'
    print('termino -> expresion')


def p_termino_multiplicacion(p):
    'termino : termino MULTIPLICACION elemento'
    print('termino * elemento -> termino')


def p_termino_division(p):
    'termino : termino DIVISION elemento'
    print('termino / elemento -> termino')


def p_termino_elemento(p):
    'termino : elemento'
    print('elemento -> termino')


def p_elemento_expresion(p):
    'elemento : A_PARENTESIS expresion C_PARENTESIS'
    print('( expresion ) -> elemento')


def p_elemento(p):
    '''elemento : N_ENTERO
                | VARIABLE
                | N_FLOAT
                | CADENA
    '''
    print(f'{p.slice[1].type} -> elemento') 
    p[0] = p[1]
    
    
def p_lista_variables(p):
    '''lista_variables : VARIABLE SEPARADOR_VARIABLES lista_variables
                       | VARIABLE
    '''
    print(f'{p.slice[1].type} -> lista_variables')
    

def p_tipo_dato(p):
    '''tipo_dato : FLOAT
                | INT
                | STRING
    '''
    print(f'{p.slice[1].type} -> tipo_dato')


# Error rule for syntax errors
def p_error(p):
    raise Exception(f"Error en la linea {p.lineno or ''} at {p.value or ''}")


def ejecutar_parser():
    # Build the parser
    parser = yacc.yacc()
    path_parser = Path("./resources/parser_test.txt")
    code = path_parser.read_text()
    parser.parse(code)
