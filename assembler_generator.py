from pathlib import Path
from typing import List, Tuple, Dict, Any
from semantic_context import SEM
from ast_node import ASTNode


def generate_asembler(ast_root) -> Path:
    """Generate a first-cut assembler file from the AST.

    For now, this creates a minimal skeleton that links against the provided
    numbers.asm library and includes number.asm macros. It serves as the
    integration hook for future codegen.
    """
    out_dir = Path('assembler_final')
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / 'final.asm'

    # Build data segment from declared symbols (variables only)
    data_lines: List[str] = []

    def sanitize_label(name: str) -> str:
        return ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in name)

    for name, info in SEM.symbols.items():
        # Only include declared variables (not lexer-made constants like _123)
        if name.startswith('_'):
            continue
        t = info.get('tipo', '')
        lab = sanitize_label(name)
        if t == 'Int' or t == 'DateConverted':
            data_lines.append(f'    {lab:<16} dd  ?')
        elif t == 'Float':
            data_lines.append(f'    {lab:<16} dd  ?')
        elif t == 'String':
            data_lines.append(f'    {lab:<16} db  MAXTEXTSIZE dup (?),\'$\'')
        elif t == 'Bool':
            data_lines.append(f'    {lab:<16} db  ?')

    # Literal message pool created while walking
    msg_counter = {'i': 0}
    msg_defs: List[str] = []

    def new_msg_label(text: str) -> str:
        msg_counter['i'] += 1
        lab = f'T_msg{msg_counter["i"]}'
        safe = text.replace('"', '\\"')
        msg_defs.append(f'    {lab:<16} db  "{safe}",\'$\'')
        return lab

    # Gather temp variables used in AST (e.g., _t1)
    temp_vars: Dict[str, str] = {}

    def collect_temps(n: Any):
        if isinstance(n, ASTNode):
            # assignment to temp or use of temp
            if n.nodetype == ':=' and isinstance(n.children[0], str) and n.children[0].startswith('_t'):
                temp_vars[n.children[0]] = 'dd'
            for ch in n.children:
                collect_temps(ch)
        elif isinstance(n, list):
            for ch in n:
                collect_temps(ch)

    collect_temps(ast_root)

    for tv in sorted(temp_vars):
        data_lines.append(f'    {sanitize_label(tv):<16} dd  ?')

    # Code emission helpers
    code: List[str] = []

    label_counter = {'i': 0}
    def new_label(prefix: str = 'L') -> str:
        label_counter['i'] += 1
        return f'{prefix}_{label_counter["i"]}'

    def emit_write_string(text: str):
        lbl = new_msg_label(text)
        code.append(f'    mov dx,OFFSET {lbl}')
        code.append('    mov ah,9')
        code.append('    int 21h')
        code.append('    newLine 1')

    # Track if we added a temp for Bool reads
    read_bool_tmp_added = {'v': False}

    def emit_read_var(varname: str):
        t = SEM.symbols.get(varname, {}).get('tipo', '')
        v = sanitize_label(varname)
        if t == 'Int' or t == 'DateConverted':
            code.append(f'    GetInteger {v}')
        elif t == 'Float':
            code.append(f'    GetFloat {v}')
        elif t == 'String':
            code.append(f'    getString {v}')
        elif t == 'Bool':
            # Read as integer into temp, then store 0/1 into the bool var
            if not read_bool_tmp_added['v']:
                data_lines.append(f'    READ_BOOL_TMP   dd  ?')
                read_bool_tmp_added['v'] = True
            code.append(f'    GetInteger READ_BOOL_TMP')
            lbl_set = new_label('LBR')
            code.append(f'    mov eax, dword ptr READ_BOOL_TMP')
            code.append('    cmp eax, 0')
            code.append('    mov al, 0')
            code.append(f'    JE {lbl_set}')
            code.append('    mov al, 1')
            code.append(f'{lbl_set}:')
            code.append(f'    mov byte ptr {v}, al')
        else:
            code.append(f'    ; TODO read unsupported type for {v}')

    def emit_write_var(varname: str):
        t = SEM.symbols.get(varname, {}).get('tipo', '')
        v = sanitize_label(varname)
        if t == 'Int' or t == 'DateConverted':
            code.append(f'    DisplayInteger {v}')
            code.append('    newLine 1')
        elif t == 'Float':
            # default to 2 decimal places
            code.append(f'    DisplayFloat {v}, 2')
            code.append('    newLine 1')
        else:
            # Unsupported types for write(var): only numeric allowed per spec
            code.append(f'    ; write unsupported type {t} for {v}')

    def emit_assign(lhs: str, rhs: Any):
        lt = SEM.symbols.get(lhs, {}).get('tipo', '')
        ld = sanitize_label(lhs)
        if isinstance(rhs, ASTNode):
            # Variable or literal wrapped in ASTNode.nodetype as string
            rn = rhs.nodetype
        else:
            rn = str(rhs)

        # Bool := true/false
        if lt == 'Bool' and isinstance(rhs, ASTNode) and rhs.nodetype in ('true', 'false'):
            val = '1' if rhs.nodetype == 'true' else '0'
            code.append(f'    mov byte ptr {ld}, {val}')
            return

        # Bool := Bool variable
        if lt == 'Bool' and rn in SEM.symbols and SEM.symbols.get(rn, {}).get('tipo', '') == 'Bool':
            rs = sanitize_label(rn)
            code.append(f'    mov al, byte ptr {rs}')
            code.append(f'    mov byte ptr {ld}, al')
            return

        # variable := variable
        if rn in SEM.symbols and not rn.startswith('"'):
            rs = sanitize_label(rn)
            rt = SEM.symbols.get(rn, {}).get('tipo', '')
            if lt == 'Int' and rt == 'Int':
                code.append(f'    mov eax, dword ptr {rs}')
                code.append(f'    mov dword ptr {ld}, eax')
            elif lt == 'Float' and rt == 'Float':
                code.append(f'    fld {rs}')
                code.append(f'    fstp {ld}')
            else:
                code.append(f'    ; TODO assign {lt} := {rt}')
            return

        # variable := integer literal
        try:
            ival = int(rn)
            if lt == 'Int' or lt == 'DateConverted':
                code.append(f'    mov dword ptr {ld}, {ival}')
                return
        except Exception:
            pass

        # variable := float literal (not fully supported in v1)
        try:
            fval = float(rn)
            if lt == 'Float':
                const_lab = f'FCONST_{abs(hash(rn)) & 0xFFFF:04X}'
                # Place const in data
                msg_defs.append(f'    {const_lab:<16} dd  {fval}')
                code.append(f'    fld {const_lab}')
                code.append(f'    fstp {ld}')
                return
        except Exception:
            pass

        # Fallback
        code.append(f'    ; TODO assign unsupported RHS for {ld}')

    def eval_int(n: ASTNode):
        # Result in EAX
        if not isinstance(n, ASTNode):
            # literal string number
            try:
                ival = int(str(n))
                code.append(f'    mov eax, {ival}')
                return
            except Exception:
                pass
        nt = n.nodetype if isinstance(n, ASTNode) else str(n)
        # variable
        if isinstance(n, ASTNode) and not n.children and nt in SEM.symbols:
            code.append(f'    mov eax, dword ptr {sanitize_label(nt)}')
            return
        # literal int
        try:
            ival = int(nt)
            code.append(f'    mov eax, {ival}')
            return
        except Exception:
            pass
        # binary ops: +,-,*,/
        if nt in ('+', '-', '*', '/') and len(n.children) == 2:
            left, right = n.children
            eval_int(left)
            code.append('    push eax')
            eval_int(right)
            code.append('    mov ebx, eax')
            code.append('    pop eax')
            if nt == '+':
                code.append('    add eax, ebx')
            elif nt == '-':
                code.append('    sub eax, ebx')
            elif nt == '*':
                code.append('    imul eax, ebx')
            else:  # '/'
                code.append('    cdq')
                code.append('    idiv ebx')
            return
        code.append('    ; TODO unsupported int expr')

    float_consts: Dict[str, str] = {}
    def const_float_label(v: float) -> str:
        key = f'{v}'
        if key not in float_consts:
            lab = f'FCONST_{len(float_consts)+1:04d}'
            msg_defs.append(f'    {lab:<16} dd  {v}')
            float_consts[key] = lab
        return float_consts[key]

    def eval_float(n: ASTNode):
        # Leave result on ST(0)
        nt = n.nodetype if isinstance(n, ASTNode) else str(n)
        # variable
        if isinstance(n, ASTNode) and not n.children and nt in SEM.symbols:
            code.append(f'    fld {sanitize_label(nt)}')
            return
        # literal float
        try:
            fval = float(nt)
            lab = const_float_label(fval)
            code.append(f'    fld {lab}')
            return
        except Exception:
            pass
        # binary ops
        if nt in ('+', '-', '*', '/') and len(n.children) == 2:
            left, right = n.children
            eval_float(left)
            eval_float(right)
            if nt == '+':
                code.append('    faddp st(1), st')
            elif nt == '-':
                code.append('    fsubp st(1), st')
            elif nt == '*':
                code.append('    fmulp st(1), st')
            else:
                code.append('    fdivp st(1), st')
            return
        code.append('    ; TODO unsupported float expr')

    def emit_compare_numeric(op: str, left: ASTNode, right: ASTNode, true_lbl: str, false_lbl: str, dtype_left: str):
        if dtype_left == 'Float':
            eval_float(left)
            eval_float(right)
            code.append('    fxch')
            code.append('    fcomp')
            code.append('    fstsw ax')
            code.append('    ffree st(0)')
            code.append('    sahf')
            jmp = {
                '==': 'JE',
                '<>': 'JNE',
                '<': 'JB',
                '<=': 'JBE',
                '>': 'JA',
                '>=': 'JAE',
            }[op]
            code.append(f'    {jmp} {true_lbl}')
            code.append(f'    JMP {false_lbl}')
        else:
            eval_int(left)
            code.append('    push eax')
            eval_int(right)
            code.append('    mov ebx, eax')
            code.append('    pop eax')
            code.append('    cmp eax, ebx')
            jmp = {
                '==': 'JE',
                '<>': 'JNE',
                '<': 'JL',
                '<=': 'JLE',
                '>': 'JG',
                '>=': 'JGE',
            }[op]
            code.append(f'    {jmp} {true_lbl}')
            code.append(f'    JMP {false_lbl}')

    def emit_condition(n: ASTNode, true_lbl: str, false_lbl: str):
        # Handle logical AND/OR short-circuit
        if n.nodetype in ('AND', 'OR') and len(n.children) == 2:
            a, b = n.children
            if n.nodetype == 'AND':
                mid = new_label('L')
                emit_condition(a, mid, false_lbl)
                code.append(f'{mid}:')
                emit_condition(b, true_lbl, false_lbl)
            else:  # OR
                mid = new_label('L')
                emit_condition(a, true_lbl, mid)
                code.append(f'{mid}:')
                emit_condition(b, true_lbl, false_lbl)
            return
        # NOT as comparator inversion or child negation is normalized earlier; fall back to negation
        if n.nodetype == 'CondNot' and n.children:
            emit_condition(n.children[0], false_lbl, true_lbl)
            return
        # Equality between Bool var and literal
        if n.nodetype == '==':
            l, r = n.children
            # Bool compare case: var == true/false
            if isinstance(l, ASTNode) and not l.children and l.nodetype in SEM.symbols and SEM.symbols.get(l.nodetype, {}).get('tipo') == 'Bool' \
               and isinstance(r, ASTNode) and r.nodetype in ('true', 'false'):
                code.append(f'    mov al, byte ptr {sanitize_label(l.nodetype)}')
                code.append(f'    cmp al, {1 if r.nodetype=="true" else 0}')
                code.append(f'    JE {true_lbl}')
                code.append(f'    JMP {false_lbl}')
                return
        # Numeric or general comparisons
        if n.nodetype in ('==','<>','<','>','<=','>=') and len(n.children) == 2:
            l, r = n.children
            # Guess dtype from left symbol/type (fallback Int)
            dtype = 'Int'
            if isinstance(l, ASTNode) and not l.children and l.nodetype in SEM.symbols:
                dtype = SEM.symbols.get(l.nodetype, {}).get('tipo', 'Int')
            emit_compare_numeric(n.nodetype, l, r, true_lbl, false_lbl, dtype)
            return
        # Fallback: assume boolean variable
        if not n.children and n.nodetype in SEM.symbols and SEM.symbols.get(n.nodetype, {}).get('tipo') == 'Bool':
            code.append(f'    mov al, byte ptr {sanitize_label(n.nodetype)}')
            code.append('    cmp al, 1')
            code.append(f'    JE {true_lbl}')
            code.append(f'    JMP {false_lbl}')
            return
        code.append('    ; TODO unsupported condition')

    def emit_block_or_stmt(n: Any):
        if isinstance(n, ASTNode) and n.nodetype == 'Block':
            for ch in n.children:
                walk(ch)
        else:
            walk(n)

    def emit_if(n: ASTNode):
        # Two shapes: [cond, Body(then, else)] or [cond, then1, then2, ...]
        cond = n.children[0]
        true_lbl = new_label('LT')
        false_lbl = new_label('LF')
        end_lbl = new_label('LE')
        emit_condition(cond, true_lbl, false_lbl)
        code.append(f'{true_lbl}:')
        if len(n.children) >= 2 and isinstance(n.children[1], ASTNode) and n.children[1].nodetype == 'Body':
            then_node, else_node = n.children[1].children
            emit_block_or_stmt(then_node)
            code.append(f'    JMP {end_lbl}')
            code.append(f'{false_lbl}:')
            emit_block_or_stmt(else_node)
        else:
            # then-only list
            for ch in n.children[1:]:
                walk(ch)
            code.append(f'    JMP {end_lbl}')
            code.append(f'{false_lbl}:')
        code.append(f'{end_lbl}:')

    def emit_while(n: ASTNode):
        start_lbl = new_label('LW')
        body_lbl = new_label('LWB')
        end_lbl = new_label('LWE')
        code.append(f'{start_lbl}:')
        emit_condition(n.children[0], body_lbl, end_lbl)
        code.append(f'{body_lbl}:')
        emit_block_or_stmt(n.children[1])
        code.append(f'    JMP {start_lbl}')
        code.append(f'{end_lbl}:')

    def walk(node: Any):
        # Walk top-level Program children
        if isinstance(node, ASTNode):
            if node.nodetype == 'Program':
                for ch in node.children:
                    walk(ch)
            elif node.nodetype == 'WRITE':
                # children ['write', arg] where arg can be a string literal or a variable name
                if len(node.children) >= 2:
                    arg = node.children[1]
                    if isinstance(arg, str) and arg in SEM.symbols:
                        # variable
                        emit_write_var(arg)
                    elif isinstance(arg, str):
                        # string literal
                        emit_write_string(arg)
            elif node.nodetype == 'READ':
                if len(node.children) >= 2 and isinstance(node.children[1], str):
                    emit_read_var(node.children[1])
            elif node.nodetype == ':=':
                if len(node.children) == 2 and isinstance(node.children[0], str):
                    lhs = node.children[0]
                    rhs = node.children[1]
                    # Assign expression results
                    ltype = SEM.symbols.get(lhs, {}).get('tipo', '')
                    if isinstance(rhs, ASTNode) and rhs.nodetype in ('+', '-', '*', '/'):
                        if ltype == 'Int' or ltype == 'DateConverted':
                            eval_int(rhs)
                            code.append(f'    mov dword ptr {sanitize_label(lhs)}, eax')
                        elif ltype == 'Float':
                            eval_float(rhs)
                            code.append(f'    fstp {sanitize_label(lhs)}')
                        else:
                            code.append('    ; TODO assign expr to non-numeric')
                    else:
                        emit_assign(lhs, rhs)
            elif node.nodetype == 'IF':
                emit_if(node)
            elif node.nodetype == 'While':
                emit_while(node)
            else:
                # TODO: support IF/While, arithmetic, comparisons
                pass

    walk(ast_root)

    # Minimal DOS real-mode program skeleton compatible with TASM/TLINK
    asm: List[str] = []
    asm.append('include macros2.asm')
    asm.append('include number.asm')
    asm.append('')
    asm.append('.MODEL  LARGE')
    asm.append('.386')
    asm.append('.STACK 200h')
    asm.append('')
    asm.append('MAXTEXTSIZE equ 50')
    asm.append('')
    asm.append('.DATA')
    asm.append('    _msgPRESIONE    db  0DH,0AH,"Presione una tecla para continuar...",\'$\'')
    asm.append('    _NEWLINE        db  0DH,0AH,\'$\'')
    # symbols
    asm.extend(data_lines)
    # message pool and any consts
    asm.extend(msg_defs)
    asm.append('')
    asm.append('.CODE')
    asm.append('START:')
    asm.append('    mov AX,@DATA')
    asm.append('    mov DS,AX')
    asm.append('    mov ES,AX')
    asm.append('')
    # generated code
    if code:
        asm.extend(code)
    else:
        asm.append('    ; no operations generated')
    asm.append('')
    # polite exit like ejemplo.asm
    asm.append('    mov dx,OFFSET _NEWLINE')
    asm.append('    mov ah,09')
    asm.append('    int 21h')
    asm.append('    mov dx,OFFSET _msgPRESIONE')
    asm.append('    mov ah,09')
    asm.append('    int 21h')
    asm.append('    mov ah, 1')
    asm.append('    int 21h')
    asm.append('    mov ax, 4C00h')
    asm.append('    int 21h')
    asm.append('END START')
    asm_text = '\n'.join(asm) + '\n'
    out_path.write_text(asm_text, encoding='utf-8')
    return out_path
