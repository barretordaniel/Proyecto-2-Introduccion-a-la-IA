# -*- coding: utf-8 -*-
"""
Pruebas automáticas de los motores de inferencia.

1. Equivalencia: para miles de conjuntos aleatorios de hechos iniciales y para CADA hecho
   derivable de la KB, el motor hacia adelante y el motor hacia atrás deben dar la misma
   respuesta, y esta debe coincidir con la clausura deductiva calculada de forma independiente.
2. Robustez ante ciclos: con una KB cíclica ambos motores terminan y no deducen nada falso.
3. Control de profundidad: con un tope pequeño el motor hacia atrás termina y falla de forma segura.

Uso:  python pruebas_equivalencia.py
"""
import json
import os
import random
import tempfile

from proyecto_inferencia_final import MotorInferencia, RUTA_KB


def clausura(reglas, hechos):
    """Punto fijo calculado de forma independiente a los motores (referencia)."""
    memoria, cambio = set(hechos), True
    while cambio:
        cambio = False
        for r in reglas:
            if r.consecuente not in memoria and r.antecedentes <= memoria:
                memoria.add(r.consecuente)
                cambio = True
    return memoria


def prueba_equivalencia(muestras=1000, semilla=2026):
    motor = MotorInferencia(RUTA_KB)
    consecuentes = {r.consecuente for r in motor.reglas}
    antecedentes = {a for r in motor.reglas for a in r.antecedentes}
    base = sorted(antecedentes - consecuentes)
    objetivos = sorted(consecuentes)
    azar = random.Random(semilla)
    comparaciones = exitos = 0
    for _ in range(muestras):
        p = azar.choice([0.3, 0.5, 0.7, 0.9])
        delta = {h for h in base if azar.random() < p}
        esperado = clausura(motor.reglas, delta)
        for obj in objetivos:
            adelante = motor.ejecutar_inferencia(delta, obj)
            atras = motor.ejecutar_inferencia_atras(delta, obj)
            assert adelante == atras == (obj in esperado), (sorted(delta), obj, adelante, atras)
            comparaciones += 1
            exitos += adelante
    print(f"[OK] Equivalencia: {muestras} conjuntos de hechos x {len(objetivos)} objetivos = "
          f"{comparaciones} comparaciones ({exitos} derivables, {comparaciones - exitos} no derivables)")


def prueba_ciclos():
    kb = {"reglas": [
        {"id": "C1", "antecedentes": ["B", "X"], "consecuente": "A"},
        {"id": "C2", "antecedentes": ["A", "Y"], "consecuente": "B"},
        {"id": "C3", "antecedentes": ["X", "Y"], "consecuente": "Z"},
    ]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(kb, f)
        ruta = f.name
    try:
        motor = MotorInferencia(ruta)
        assert motor.ejecutar_inferencia({"X", "Y"}, "A") is False
        assert motor.ejecutar_inferencia_atras({"X", "Y"}, "A") is False   # termina pese al ciclo A<->B
        assert motor.ejecutar_inferencia_atras({"X", "Y"}, "Z") is True    # y sigue probando lo demás
        assert motor.ejecutar_inferencia_atras({"X", "Y", "B"}, "A") is True  # el ciclo se rompe con un hecho
    finally:
        os.remove(ruta)
    print("[OK] Ciclos: ambos motores terminan y no deducen hechos falsos con una KB cíclica")


def prueba_profundidad():
    motor = MotorInferencia(RUTA_KB)
    delta = ["Fiebre", "Escalofrios", "Dolor_Muscular", "Fatiga", "Perdida_Olfato",
             "Dificultad_Respiratoria", "Saturacion_Oxigeno_Baja"]
    original = motor.PROFUNDIDAD_MAXIMA
    try:
        motor.PROFUNDIDAD_MAXIMA = 3  # la prueba de Alerta_COVID_Grave necesita 5 niveles
        assert motor.ejecutar_inferencia_atras(delta, "Alerta_COVID_Grave") is False
        assert any("profundidad máxima" in linea for linea in motor.traza_explicacion)
    finally:
        motor.PROFUNDIDAD_MAXIMA = original
    assert motor.ejecutar_inferencia_atras(delta, "Alerta_COVID_Grave") is True
    print("[OK] Profundidad: con tope 3 el motor hacia atrás corta la búsqueda; con el tope por defecto prueba el objetivo")


if __name__ == "__main__":
    prueba_equivalencia()
    prueba_ciclos()
    prueba_profundidad()
    print("Todas las pruebas pasaron.")
