def collect_var_names(lista):
    names = []
    if isinstance(lista, list):
        for n in lista:
            names.append(n)
    else:
        names.append(lista)
    return names


_temp_counter = {'i': 0}


def new_temp():
    _temp_counter['i'] += 1
    name = f"_t{_temp_counter['i']}"
    return name

def is_numeric(t):
    return t in ('Int', 'Float', 'DateConverted')  # DateConverted behaves numeric


def combine_numeric(t1, t2, lineno: int, op: str):
    if not (is_numeric(t1) and is_numeric(t2)):
        raise Exception(f"Error semántico (línea {lineno}): operador '{op}' requiere operandos numéricos, recibió {t1} y {t2}")
    # Result type: Float if any Float, else Int
    if 'Float' in (t1, t2):
        return 'Float'
    return 'Int'


def ensure_assign_compatible(lhs_t: str, rhs_t: str, lineno: int, lhs_name: str):
    if lhs_t != rhs_t:
        raise Exception(
            f"Error semántico (línea {lineno}): incompatibilidad de tipos al asignar a '{lhs_name}': {lhs_t} := {rhs_t}")
