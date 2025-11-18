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
    isEqual          db  ?
    _t1              dd  ?
    _t2              dd  ?
    _t3              dd  ?
    _t4              dd  ?
    T_msg1           db  "a es mayor que c",'$'
    T_msg2           db  "a no es mayor que c",'$'
    T_msg3           db  "test -if anidado-",'$'
    T_msg4           db  "a es mayor que c y b",'$'
    T_msg5           db  "test -and-",'$'
    T_msg6           db  "a es mayor que c y b",'$'
    T_msg7           db  "test -or-",'$'
    T_msg8           db  "a es mayor que c o b",'$'
    T_msg9           db  "test -not-",'$'
    T_msg10          db  "a no es mayor que c",'$'
    T_msg11          db  "hola",'$'
    T_msg12          db  "is equal expressions",'$'

.CODE
START:
    mov AX,@DATA
    mov DS,AX
    mov ES,AX

    mov dword ptr a, 10
    mov dword ptr b, 12
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
    mov dx,OFFSET T_msg1
    mov ah,9
    int 21h
    newLine 1
    JMP LE_3
LF_2:
    mov dx,OFFSET T_msg2
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
    mov dx,OFFSET T_msg3
    mov ah,9
    int 21h
    newLine 1
    mov dx,OFFSET T_msg4
    mov ah,9
    int 21h
    newLine 1
    JMP LE_9
LF_8:
LE_9:
    JMP LE_6
LF_5:
LE_6:
    ; TODO unsupported condition
LT_10:
    mov dx,OFFSET T_msg5
    mov ah,9
    int 21h
    newLine 1
    mov dx,OFFSET T_msg6
    mov ah,9
    int 21h
    newLine 1
    JMP LE_12
LF_11:
LE_12:
    ; TODO unsupported condition
LT_13:
    mov dx,OFFSET T_msg7
    mov ah,9
    int 21h
    newLine 1
    mov dx,OFFSET T_msg8
    mov ah,9
    int 21h
    newLine 1
    JMP LE_15
LF_14:
LE_15:
    mov eax, dword ptr a
    push eax
    mov eax, dword ptr c
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JLE LT_16
    JMP LF_17
LT_16:
    mov dx,OFFSET T_msg9
    mov ah,9
    int 21h
    newLine 1
    mov dx,OFFSET T_msg10
    mov ah,9
    int 21h
    newLine 1
    JMP LE_18
LF_17:
LE_18:
    mov dword ptr d, 0
LW_19:
    mov eax, dword ptr d
    push eax
    mov eax, 3
    mov ebx, eax
    pop eax
    cmp eax, ebx
    JL LWB_20
    JMP LWE_21
LWB_20:
    mov dx,OFFSET T_msg11
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
    JMP LW_19
LWE_21:
    mov al, byte ptr isEqual
    cmp al, 1
    JE LT_22
    JMP LF_23
LT_22:
    mov dx,OFFSET T_msg12
    mov ah,9
    int 21h
    newLine 1
    JMP LE_24
LF_23:
LE_24:

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
