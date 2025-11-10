import ply.lex as lex
from pathlib import Path
import re

reserved = {
    'while': 'WHILE',
    'if': 'IF',
    'else': 'ELSE',
    'write': 'WRITE',
    'read': 'READ',
    'or': 'OR',
    'and': 'AND',
    'not': 'NOT',
    'init': 'INIT',
    'Float': 'FLOAT',
    'Int': 'INT',
    'String': 'STRING',
    'DateConverted': 'DATE_CONVERTED',
    'equalExpressions': 'EQUAL_EXPRESSIONS',
    'convDate': 'CONV_DATE',
    'Bool': 'BOOLEAN',
}

tokens = [
    'A_PARENTESIS',
    'C_PARENTESIS',
    'A_LLAVE',
    'C_LLAVE',
    'ASIGNACION',
    'N_ENTERO',
    'N_FLOAT',
    'CADENA',
    'DATE',
    'VARIABLE',
    'MENOS',
    'DIVISION',
    'MULTIPLICACION',
    'MAS',
    'COMPARADOR',
    'ASIGNACION_TIPO',
    'SEPARADOR_VARIABLES',
] + list(reserved.values())


# Expresiones regulares para TOKENS simples
t_MENOS = r'-'
t_MAS = r'\+'
t_MULTIPLICACION = r'\*'
t_DIVISION = r'/'
t_A_PARENTESIS = r'\('
t_C_PARENTESIS = r'\)'
t_A_LLAVE = r'\{'
t_C_LLAVE = r'\}'
t_ASIGNACION = r':='
t_COMPARADOR = r'==|<>|<=|>=|<|>'
t_ASIGNACION_TIPO = r':'
t_SEPARADOR_VARIABLES = r','


def t_VARIABLE(t):
    r'[a-zA-Z](\w|_)*'
    t.type = reserved.get(t.value, 'VARIABLE')
    return t

def t_N_FLOAT(t):
    r'(\d+\.\d*|\.\d+)'
    t.value = float(t.value)
    if not (-3.4e38 <= t.value <= 3.4e38):
        raise Exception(f"Float fuera de rango (32 bits) '{t.value}' en la linea: {t.lexer.lineno}")
    return t

def t_DATE(t):
    r'\d{2}-\d{2}-\d{4}'
    dia, mes, anio = map(int, t.value.split('-'))
    if not (1 <= dia <= 31 and 1 <= mes <= 12 and 1000 <= anio <= 9999):
        raise Exception(f"Fecha inválida '{t.value}' en la linea: {t.lexer.lineno}")
    return t

def t_N_ENTERO(t):
    r'-?\d+'
    # Allow optional leading '-' for negative integers. The '-' token is still
    # recognized separately when not followed by digits (e.g. as operator).
    t.value = int(t.value)
    if not (-32768 <= t.value <= 32767):
        raise Exception(f"Entero fuera de rango (16 bits signed) '{t.value}' en la linea: {t.lexer.lineno}")
    return t

def t_CADENA(t):
    r'\"([^"\n]*)\"'
    # t.value includes the surrounding quotes, remove them for storage
    raw = t.value[1:-1]
    max_len = 50
    if len(raw) > max_len:
        raise Exception(f"Cadena demasiado larga (max {max_len}) '{raw}' en la linea: {t.lexer.lineno}")
    t.value = raw
    return t


# Regla que cuenta la cantidad de lineas
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Regla que ignora comentarios multilínea
def t_COMENTARIO(t):
    r'\#\+(.|\n)*?\+\#'
    pass

# Ignorar tabulaciones y espacios
t_ignore = ' \t'

# Manejo de errores
def t_error(t):
    raise Exception(f"Caracter invalido '{t.value[0]}' en la linea: {t.lexer.lineno}")


# Build the lexer
lexer = lex.lex(reflags=re.DOTALL)


def ejecutar_lexer(code):
    lexer.input(code)
    tabla_simbolos = []
    while True:
        token = lexer.token()
        if not token:
            break
        print(f'TOKEN: {token.type} LEXEMA: {token.value}')
        # Guardar variables (solo nombre)
        if token.type == 'VARIABLE':
            tabla_simbolos.append({'nombre': token.value, 'tipo': '', 'valor': ''})
        # Guardar constantes (nombre, tipo, valor)
        elif token.type in ('N_ENTERO', 'N_FLOAT', 'CADENA', 'DATE', 'DATE_CONVERTED'):
            tipo = {
                'N_ENTERO': 'Int',
                'N_FLOAT': 'Float',
                'CADENA': 'String',
                'DATE': 'Date',
                'DATE_CONVERTED': 'DateConverted',
                'BOOLEAN': 'Bool'
            }[token.type]
            nombre_constante = f"_{token.value}"
            tabla_simbolos.append({'nombre': nombre_constante, 'tipo': tipo, 'valor': token.value})

    # Escribir la tabla de símbolos en un archivo
    output_path = Path('./resources/tabla_simbolos.txt')
    with output_path.open('w', encoding='utf-8') as f:
        f.write(f"{'Nombre':<20}{'Tipo de Dato':<15}{'Valor':<30}\n")
        f.write('-' * 65 + '\n')
        for entry in tabla_simbolos:
            f.write(f"{entry['nombre']:<20}{entry['tipo']:<15}{str(entry['valor']):<30}\n")
