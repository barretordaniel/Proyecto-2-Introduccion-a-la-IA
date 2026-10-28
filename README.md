# Proyecto Aplicativo 2 · Motor de inferencia simbólica

Introducción a la Inteligencia Artificial · Pontificia Universidad Javeriana

Motor de inferencia de propósito general con encadenamiento hacia adelante (*forward chaining*) y hacia atrás (*backward chaining*) sobre una base de conocimiento médica de cláusulas de Horn. El sistema resuelve la consecuencia lógica `KB ⊨ α`: dado un conjunto de síntomas Δ y una hipótesis α, determina si α se deriva de Δ con las reglas de la KB y explica el razonamiento con una traza.

## Contenido

| Archivo | Descripción |
|---|---|
| `proyecto_inferencia_final.py` | Código fuente comentado: plantilla, `ejecutar_inferencia()` (hacia adelante), `ejecutar_inferencia_atras()` (hacia atrás) y casos clínicos de prueba. |
| `base_conocimiento.json` | Base de conocimiento externa: 65 reglas de Horn en 4 niveles de inferencia. |
| `validar_kb.py` | Auditoría automática de la KB: forma de Horn, aciclicidad, alcanzabilidad, profundidad y alertas. |
| `pruebas_equivalencia.py` | Pruebas de equivalencia entre ambos motores, robustez ante ciclos y control de profundidad. |


## Uso

Solo requiere Python 3 (biblioteca estándar).

```bash
python proyecto_inferencia_final.py             # corre los casos clínicos con ambos motores
python proyecto_inferencia_final.py --exportar  # además guarda cada traza en trazas/
python validar_kb.py                            # audita la base de conocimiento
python pruebas_equivalencia.py                  # compara ambos motores
```

Uso desde código:

```python
from proyecto_inferencia_final import MotorInferencia, RUTA_KB

motor = MotorInferencia(RUTA_KB)
sintomas = ["Fiebre", "Escalofrios", "Dolor_Muscular", "Fatiga", "Inicio_Brusco"]

motor.ejecutar_inferencia(sintomas, "Gripe")        # True
print(motor.exportar_traza())                       # traza de explicación

motor.ejecutar_inferencia_atras(sintomas, "Gripe")  # True
print(motor.exportar_traza())
```

## Base de conocimiento

- 36 hechos de entrada (síntomas, antecedentes y criterios de gravedad), 10 enfermedades y 26 resultados de nivel 4 (subtipos, indicaciones y alertas).
- Niveles: 1) hechos → signos, 2) signos → síndromes, 3) síndromes + hecho diferenciador → enfermedades, 4) enfermedad → subtipo, indicación o alerta. Los resultados finales requieren entre 4 y 5 inferencias encadenadas.
- Formato de cada regla: `id`, `antecedentes` (unidos por AND), `consecuente` (único), más `nivel` y `descripcion`, que el motor ignora y sirven para la auditoría.

Es una simplificación didáctica y no una herramienta de diagnóstico médico.
