"""Verifica rotas duplicadas"""
import re

with open("app.py", "r", encoding="utf-8") as f:
    linhas = f.readlines()

print("=== Ocorrências de /cerebro ===")
for i, linha in enumerate(linhas, 1):
    if '@app.route("/cerebro"' in linha or "@app.route('/cerebro'" in linha:
        print("Linha {}: {}".format(i, linha.rstrip()))

print("\n=== Ocorrências de cerebro_page ===")
for i, linha in enumerate(linhas, 1):
    if 'def cerebro_page' in linha:
        print("Linha {}: {}".format(i, linha.rstrip()))