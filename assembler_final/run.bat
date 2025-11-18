PATH=C:\TASM;

rem Assemble runtime support and generated program
tasm numbers.asm
tasm final.asm

rem Link final with numbers support
tlink final.obj numbers.obj

rem Run and cleanup
final.exe
del final.obj 
del numbers.obj 
del final.exe
del final.map
