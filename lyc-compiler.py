from pathlib import Path

from parser import ejecutar_parser
from lexer import ejecutar_lexer


def main():
	path = Path('./resources/prueba.txt')
	code = path.read_text()

	# Run lexer (prints tokens) and parser on the exact same input
	ejecutar_lexer(code)
	ejecutar_parser(code)


if __name__ == '__main__':
	main()
