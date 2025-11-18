include macros2.asm
include number.asm

.MODEL  LARGE
.386
.STACK 200h

MAXTEXTSIZE equ 50

.DATA
    _msgPRESIONE    db  0DH,0AH,"Presione una tecla para continuar...",'$'
    _NEWLINE        db  0DH,0AH,'$'
    a                dd  ?
    b                dd  ?
    c                dd  ?
    d                dd  ?
    e                dd  ?
    isEqual          db  ?
    cad              db  MAXTEXTSIZE dup (?),'$'
    _t1              dd  ?
    _t2              dd  ?
    _t3              dd  ?
    _t4              dd  ?
    T_msg1           db  "Ingrese el valor de a: ",'$'
    T_msg2           db  "Ingrese el valor de b: ",'$'
    T_msg3           db  "Ingrese el valor de c: ",'$'
    T_msg4           db  "a es mayor que c",'$'
    T_msg5           db  "a no es mayor que c",'$'
    T_msg6           db  "test -if anidado-",'$'
    T_msg7           db  "a es mayor que c y b",'$'
    T_msg8           db  "test -and-",'$'
    T_msg9           db  "a es mayor que c y b",'$'
    T_msg10          db  "test -or-",'$'
    T_msg11          db  "a es mayor que c o b",'$'
    T_msg12          db  "test -not-",'$'
    T_msg13          db  "a no es mayor que c",'$'
    T_msg14          db  "hola",'$'
    T_msg15          db  "is equal expressions",'$'

.CODE
START:
    mov AX,@DATA
    mov DS,AX
    mov ES,AX

    mov dx,OFFSET T_msg1
    mov ah,9
    int 21h
    newLine 1
    GetInteger a
    mov dx,OFFSET T_msg2
    mov ah,9
    int 21h
    newLine 1
    GetInteger b
    mov dx,OFFSET T_msg3
    mov ah,9
    int 21h
    newLine 1
    GetInteger c
    mov eax, dword ptr a
    push eax
    mov eax, dword ptr c
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JG LT_1
    JMP LF_2
LT_1:
    mov dx,OFFSET T_msg4
    mov ah,9
    int 21h
    newLine 1
    JMP LE_3
LF_2:
    mov dx,OFFSET T_msg5
    mov ah,9
    int 21h
    newLine 1
LE_3:
    mov eax, dword ptr a
    push eax
    mov eax, dword ptr c
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JG LT_4
    JMP LF_5
LT_4:
    mov eax, dword ptr a
    push eax
    mov eax, dword ptr b
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JG LT_7
    JMP LF_8
LT_7:
    mov dx,OFFSET T_msg6
    mov ah,9
    int 21h
    newLine 1
    mov dx,OFFSET T_msg7
    mov ah,9
    int 21h
    newLine 1
    JMP LE_9
LF_8:
LE_9:
    JMP LE_6
LF_5:
LE_6:
    mov eax, dword ptr a
    push eax
    mov eax, dword ptr b
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JG L_13
    JMP LF_11
L_13:
    mov eax, dword ptr a
    push eax
    mov eax, dword ptr c
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JG LT_10
    JMP LF_11
LT_10:
    mov dx,OFFSET T_msg8
    mov ah,9
    int 21h
    newLine 1
    mov dx,OFFSET T_msg9
    mov ah,9
    int 21h
    newLine 1
    JMP LE_12
LF_11:
LE_12:
    mov eax, dword ptr a
    push eax
    mov eax, dword ptr b
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JG LT_14
    JMP L_17
L_17:
    mov eax, dword ptr a
    push eax
    mov eax, dword ptr c
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JG LT_14
    JMP LF_15
LT_14:
    mov dx,OFFSET T_msg10
    mov ah,9
    int 21h
    newLine 1
    mov dx,OFFSET T_msg11
    mov ah,9
    int 21h
    newLine 1
    JMP LE_16
LF_15:
LE_16:
    mov eax, dword ptr a
    push eax
    mov eax, dword ptr c
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JLE LT_18
    JMP LF_19
LT_18:
    mov dx,OFFSET T_msg12
    mov ah,9
    int 21h
    newLine 1
    mov dx,OFFSET T_msg13
    mov ah,9
    int 21h
    newLine 1
    JMP LE_20
LF_19:
LE_20:
    mov dword ptr d, 0
LW_21:
    mov eax, dword ptr d
    push eax
    mov eax, 3
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JL LWB_22
    JMP LWE_23
LWB_22:
    mov dx,OFFSET T_msg14
    mov ah,9
    int 21h
    newLine 1
    mov eax, dword ptr d
    push eax
    mov eax, 1
    mov ebx, eax
    pop eax
    add eax, ebx
    mov dword ptr d, eax
    JMP LW_21
LWE_23:
    mov al, byte ptr isEqual
    cmp al, 1
    JE LT_24
    JMP LF_25
LT_24:
    mov dx,OFFSET T_msg15
    mov ah,9
    int 21h
    newLine 1
    JMP LE_26
LF_25:
LE_26:

    mov dx,OFFSET _NEWLINE
    mov ah,09
    int 21h
    mov dx,OFFSET _msgPRESIONE
    mov ah,09
    int 21h
    mov ah, 1
    int 21h
    mov ax, 4C00h
    int 21h
END START
