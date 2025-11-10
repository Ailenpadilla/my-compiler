from pathlib import Path


class SemanticContext:
    def __init__(self):
        # symbols: name -> { 'tipo': str, 'valor': any }
        self.symbols = {}
        # track duplicates in declarations
        self.declared = set()

    def load_from_table(self, path: Path):
        if not path.exists():
            return
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
        # Skip header (first two lines)
        for line in lines[2:]:
            if not line.strip():
                continue
            # Fixed-width columns used by lexer when writing the table
            name = line[0:20].strip()
            tipo = line[20:35].strip()
            valor = line[35:].strip()
            self.symbols[name] = {'tipo': tipo, 'valor': valor}
            if tipo:
                self.declared.add(name)

    def set_decl(self, name: str, dtype: str, lineno: int):
        # Duplicate definition if already declared with a type
        if name in self.declared:
            raise Exception(f"Error semántico (línea {lineno}): variable '{name}' ya declarada")
        # ensure entry exists in table for consistency
        entry = self.symbols.get(name, {'tipo': '', 'valor': ''})
        entry['tipo'] = dtype
        self.symbols[name] = entry
        self.declared.add(name)

    def ensure_declared(self, name: str, lineno: int):
        entry = self.symbols.get(name)
        if not entry or not entry.get('tipo'):
            raise Exception(f"Error semántico (línea {lineno}): identificador no declarado '{name}'")
        return entry['tipo']


# Singleton context used by the parser
SEM = SemanticContext()

