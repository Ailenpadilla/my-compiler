# Plantilla para TP Integrador usando PLY compiler (Python)

PLY es una implementación puramente Python de las populares herramientas de construcción de compiladores lex y yacc.

Para mas información: https://www.dabeaz.com/ply/ply.html#ply_nn1 

## Ejecución

**Requisitos**
   -Python 3.12
   -pip
   -Paquete 'ply'

Para ejecutar el codigo, sigue los siguientes pasos:

1. **Instalar dependencias**

   Si ya tenes pipenv instalado podes ejecutar:
   ```bash
   pipenv install
   ```
   Si no tenes pipenv podes instalar 'ply' globalmente
   ```bash
   pip install ply
   ```

2. **Ejecutar**

   Si estas usando pipenv
   ```bash
   pipenv shell
   ```
   ```bash
   python lyc-compiler.py
   ```

   Si instalaste 'ply' globalmente simplemente ejecuta:
   ```bash
   python lyc-compiler.py
   ```
