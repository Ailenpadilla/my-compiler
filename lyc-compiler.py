from pathlib import Path

from parser import ejecutar_parser
from assembler_generator import generate_asembler
from lexer import ejecutar_lexer


def main():
	path = Path('./resources/prueba.txt')
	code = path.read_text()

	# Run lexer (prints tokens) and parser on the exact same input
	ejecutar_lexer(code)
	ast = ejecutar_parser(code)
	try:
		asm_path = generate_asembler(ast)
		print(f'Generated assembler at {asm_path}')
	except Exception as e:
		print(f'Assembler generation failed: {e}')


if __name__ == '__main__':
	main()
