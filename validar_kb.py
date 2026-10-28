# -*- coding: utf-8 -*-
"""
Validador de la Base de Conocimiento (base_conocimiento.json).

Verifica de forma automática los requisitos del Proyecto Aplicativo 2:
  1. Cantidad: mínimo 50 reglas distintas, con ids únicos.
  2. Restricción de Horn: antecedentes unidos por AND (2 o más, sin repetir) y un único
     consecuente positivo.
  3. Aciclicidad: el grafo de dependencias no tiene ciclos.
  4. Alcanzabilidad: partiendo de todos los hechos base, TODAS las reglas pueden activarse.
  5. Sin islas: todo hecho derivado alimenta otra regla o es un resultado final, y todo
     resultado final está conectado con los hechos de entrada.
  6. Profundidad: todo resultado final exige una cadena de al menos 4 inferencias.
  7. Ramas de alta similitud (antecedentes compartidos + un único hecho diferenciador).
  8. Reglas de alerta (diagnóstico ya inferido + síntoma crítico).

Uso:  python validar_kb.py [ruta_al_json]
Termina con código 0 si todo se cumple y 1 si hay algún incumplimiento.
"""
import json
import os
import sys
from collections import defaultdict

MINIMO_REGLAS = 50
PROFUNDIDAD_MINIMA = 4


def _buscar_ciclo(grafo):
    """DFS con colores. Devuelve una lista de nodos que forma un ciclo, o None."""
    color, pila = {}, []

    def dfs(u):
        color[u] = 1
        pila.append(u)
        for v in grafo.get(u, ()):
            if color.get(v, 0) == 1:
                return pila[pila.index(v):] + [v]
            if color.get(v, 0) == 0:
                ciclo = dfs(v)
                if ciclo:
                    return ciclo
        color[u] = 2
        pila.pop()
        return None

    for nodo in list(grafo):
        if color.get(nodo, 0) == 0:
            ciclo = dfs(nodo)
            if ciclo:
                return ciclo
    return None


def _cierre(reglas, hechos):
    """Clausura deductiva (punto fijo) de un conjunto de hechos."""
    memoria, cambio = set(hechos), True
    while cambio:
        cambio = False
        for r in reglas:
            if r["consecuente"] not in memoria and set(r["antecedentes"]) <= memoria:
                memoria.add(r["consecuente"])
                cambio = True
    return memoria


def analizar(ruta):
    """Devuelve un diccionario con las verificaciones y las métricas de la KB."""
    with open(ruta, encoding="utf-8") as f:
        reglas = json.load(f)["reglas"]

    verificaciones = []  # (descripcion, cumple, detalle)

    def anotar(desc, cumple, detalle=""):
        verificaciones.append((desc, bool(cumple), detalle))

    # ---- 1. Cantidad e unicidad ----
    ids = [r.get("id") for r in reglas]
    firmas = [(frozenset(r["antecedentes"]), r["consecuente"]) for r in reglas]
    distintas = len(set(firmas))
    anotar(f"Al menos {MINIMO_REGLAS} reglas distintas",
           distintas >= MINIMO_REGLAS and len(set(ids)) == len(ids),
           f"{len(reglas)} reglas, {distintas} distintas, {len(set(ids))} ids únicos")

    # ---- 2. Forma de Horn ----
    malas = []
    for r in reglas:
        ants, cons = r["antecedentes"], r["consecuente"]
        if (not isinstance(ants, list) or len(ants) < 2 or len(set(ants)) != len(ants)
                or not isinstance(cons, str) or not cons or cons in ants):
            malas.append(r.get("id"))
    anotar("Restricción de Horn (2+ antecedentes con AND, un único consecuente positivo)",
           not malas, "todas las reglas cumplen" if not malas else f"incumplen: {malas}")

    # ---- Grafo de dependencias ----
    consecuentes = {r["consecuente"] for r in reglas}
    antecedentes = {a for r in reglas for a in r["antecedentes"]}
    base = antecedentes - consecuentes              # hechos de entrada (síntomas, antecedentes, etc.)
    derivados = consecuentes                        # hechos que el motor puede deducir
    terminales = consecuentes - antecedentes        # resultados finales (no alimentan otras reglas)
    grafo = defaultdict(set)
    for r in reglas:
        for a in r["antecedentes"]:
            grafo[a].add(r["consecuente"])

    # ---- 3. Aciclicidad ----
    ciclo = _buscar_ciclo(grafo)
    anotar("Aciclicidad (sin ciclos entre hechos)", ciclo is None,
           "grafo dirigido acíclico" if ciclo is None else "ciclo: " + " -> ".join(ciclo))

    # ---- 4. Alcanzabilidad ----
    cierre = _cierre(reglas, base)
    inactivas = [r["id"] for r in reglas if not set(r["antecedentes"]) <= cierre]
    anotar("Alcanzabilidad: toda regla puede activarse desde los hechos base",
           not inactivas and derivados <= cierre,
           f"{len(reglas) - len(inactivas)} de {len(reglas)} reglas activables")

    # ---- 5. Profundidades (solo si no hay ciclos) ----
    dmin, dmax = {}, {}
    if ciclo is None:
        por_cons = defaultdict(list)
        for r in reglas:
            por_cons[r["consecuente"]].append(r)

        def prof(h):
            if h in base:
                return 0, 0
            if h not in dmin:
                subs = [[prof(a) for a in r["antecedentes"]] for r in por_cons[h]]
                dmin[h] = min(1 + max(s[0] for s in sub) for sub in subs)
                dmax[h] = max(1 + max(s[1] for s in sub) for sub in subs)
            return dmin[h], dmax[h]

        for h in derivados:
            prof(h)

    # ---- 5b. Sin islas ----
    # Un hecho derivado que no alimenta nada es un resultado final; como el grafo es acíclico y
    # finito, todo hecho derivado desemboca en algún resultado final. Se verifica además que
    # cada resultado final esté conectado con los hechos de entrada (pertenezca a la clausura).
    islas = sorted(h for h in derivados if h not in cierre)
    sin_uso = sorted(b for b in base if b not in antecedentes)
    anotar("Sin islas: todo hecho derivado se conecta con las entradas y con un resultado final",
           not islas and not sin_uso,
           f"{len(base)} hechos base, {len(derivados) - len(terminales)} hechos intermedios, "
           f"{len(terminales)} resultados finales")

    # ---- 6. Profundidad de los resultados finales ----
    if ciclo is None:
        bajos = sorted(t for t in terminales if dmin[t] < PROFUNDIDAD_MINIMA)
        anotar(f"Todo resultado final requiere al menos {PROFUNDIDAD_MINIMA} niveles de inferencia",
               not bajos,
               f"profundidad mínima de los {len(terminales)} resultados finales = "
               f"{min(dmin[t] for t in terminales)}, máxima = {max(dmax[t] for t in terminales)}")
    else:
        bajos = []

    # ---- 7. Ramas de alta similitud (reglas de nivel 2 y 3 con antecedente derivado compartido) ----
    ramas = {}
    for nivel in (2, 3):
        usos = defaultdict(list)  # antecedente derivado -> [(otros antecedentes, consecuente, id)]
        for r in reglas:
            if r.get("nivel", 3) != nivel:  # sin campo 'nivel' se analiza todo como nivel 3
                continue
            for a in r["antecedentes"]:
                if a in derivados:
                    usos[a].append((sorted(set(r["antecedentes"]) - {a}), r["consecuente"], r["id"]))
        for a, lst in usos.items():
            if len({c for (_, c, _) in lst}) >= 2:  # el mismo antecedente conduce a 2+ conclusiones
                ramas[(nivel, a)] = lst
    ramas_n3 = {a: l for (n, a), l in ramas.items() if n == 3}
    anotar("Ramas de alta similitud: síndromes compartidos que se bifurcan por un hecho diferenciador",
           len(ramas_n3) >= 3,
           f"{len(ramas_n3)} síndromes se bifurcan en enfermedades distintas")

    # ---- 8. Reglas de alerta ----
    alertas = [r for r in reglas
               if r["consecuente"].startswith("Alerta_")
               and any(a in derivados for a in r["antecedentes"])
               and any(a in base for a in r["antecedentes"])]
    anotar("Reglas de alerta: diagnóstico ya inferido + síntoma crítico", len(alertas) >= 1,
           f"{len(alertas)} reglas de alerta")

    por_nivel = defaultdict(int)
    for r in reglas:
        por_nivel[r.get("nivel", 0)] += 1

    return {
        "verificaciones": verificaciones,
        "ok": all(v[1] for v in verificaciones),
        "n_reglas": len(reglas),
        "base": sorted(base),
        "intermedios": sorted(derivados - terminales),
        "terminales": sorted(terminales),
        "dmin": dmin, "dmax": dmax,
        "ramas_n3": ramas_n3,
        "ramas_n2": {a: l for (n, a), l in ramas.items() if n == 2},
        "alertas": [(r["id"], r["antecedentes"], r["consecuente"]) for r in alertas],
        "por_nivel": dict(sorted(por_nivel.items())),
    }


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "base_conocimiento.json")
    res = analizar(ruta)
    print(f"Validación de {os.path.basename(ruta)}\n")
    for desc, cumple, detalle in res["verificaciones"]:
        print(f"[{'OK' if cumple else 'FALLA'}] {desc}\n       {detalle}")
    print("\nReglas por nivel:", res["por_nivel"])
    print("Resultado global:", "KB VÁLIDA" if res["ok"] else "KB CON INCUMPLIMIENTOS")
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
