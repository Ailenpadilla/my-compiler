import ply.lex as lex
from pathlib import Path
import re

reserved = {
}

tokens = [
    'A_PARENTESIS',
    'C_PARENTESIS',
    'ASIGNACION',
    'N_ENTERO',
    'VARIABLE',
    'MENOS',
    'DIVISION',
    'MULTIPLICACION',
] + list(reserved.values())


# Expresiones regulares para TOKENS simples
t_MENOS = r'-'
t_MULTIPLICACION = r'\*'
t_DIVISION = r'/'
t_A_PARENTESIS = r'\('
t_C_PARENTESIS = r'\)'
t_ASIGNACION = r':='


def t_VARIABLE(t):
    r'[a-zA-Z](\w|_)*'
    t.type = reserved.get(t.value, 'VARIABLE')
    return t


def t_N_ENTERO(t):
    r'\d+'
    t.value = int(t.value)
    return t


# Regla que cuenta la cantidad de lineas
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# Ignorar tabulaciones y espacios
t_ignore = ' \t'

# Manejo de errores
def t_error(t):
    raise Exception(f"Caracter invalido '{t.value[0]}' en la linea: {t.lexer.lineno}")


# Build the lexer
lexer = lex.lex(reflags=re.DOTALL)


def ejecutar_lexer():
    path_lexter = Path('./resources/lexer_test.txt')
    data = path_lexter.read_text()
    lexer.input(data)
    while True:
        token = lexer.token()
        if not token:
            break
        print(f'TOKEN: {token.type} LEXEMA: {token.value}')
