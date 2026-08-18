"""
Verifica rotas duplicadas no app.py
"""
import re

with open("app.py", "r", encoding="utf-8") as f:
    conteudo = f.read()

# Encontrar todos os endpoints
rotas    = re.findall(r'@app\.route\("([^"]+)"', conteudo)
funcoes  = re.findall(r'^def ([a-zA-Z_]+)\(', conteudo, re.MULTILINE)

# Verificar duplicatas
print("=== ROTAS ===")
vistas = {}
for r in rotas:
    if r in vistas:
        print("DUPLICATA: {}".format(r))
    else:
        vistas[r] = True
        print("OK: {}".format(r))

print("\n=== FUNÇÕES ===")
vistas_f = {}
for f in funcoes:
    if f in vistas_f:
        print("DUPLICATA: {}".format(f))
    else:
        vistas_f[f] = True
        print("OK: {}".format(f))