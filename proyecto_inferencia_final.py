import json
import os
import sys

# ==========================================================
# PARTE 1: ESTRUCTURA DE DATOS (NO MODIFICAR)
# ==========================================================
class Regla:
    def __init__(self, id_regla, antecedentes, consecuente):
        self.id_regla = id_regla
        self.antecedentes = set(antecedentes)  
        self.consecuente = consecuente

    def __str__(self):
        return f"{self.id_regla}: {' AND '.join(self.antecedentes)} -> {self.consecuente}"

class MotorInferencia:
    def __init__(self, ruta_kb):
        self.reglas = self.cargar_kb(ruta_kb)
        self.memoria_trabajo = set()
        self.traza_explicacion = [] # Sugerencia para almacenar el orden de las reglas activadas

    def cargar_kb(self, ruta):
        """Carga las reglas desde un archivo JSON."""
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            return [Regla(r.get('id'), r['antecedentes'], r['consecuente']) for r in datos['reglas']]
        except Exception as e:
            print(f"Error al cargar la Base de Conocimiento: {e}")
            return []

    # ==========================================================
    # PARTE 2: MOTORES DE INFERENCIA (A DESARROLLAR)
    # ==========================================================

    # Tope de profundidad del encadenamiento hacia atrás. La KB es acíclica y su cadena
    # más larga tiene 5 niveles; el tope solo protege ante bases de conocimiento mal formadas.
    PROFUNDIDAD_MAXIMA = 50

    @staticmethod
    def _texto_regla(regla, orden=None):
        """Texto determinista de una regla (los conjuntos de Python no tienen orden fijo)."""
        ants = orden if orden is not None else sorted(regla.antecedentes)
        return f"{regla.id_regla}: {' AND '.join(ants)} -> {regla.consecuente}"

    def exportar_traza(self, ruta=None):
        """Devuelve la traza de la última inferencia como texto; si se da una ruta, la guarda en un archivo."""
        texto = "\n".join(self.traza_explicacion)
        if ruta:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(texto + "\n")
        return texto

    def ejecutar_inferencia(self, hechos_iniciales, objetivo):
        """
        Motor de Encadenamiento hacia Adelante (Forward Chaining).
        Retorna True si el objetivo es consecuencia lógica, False en caso contrario.
        Registra la traza de explicación (orden cronológico de las reglas disparadas).

        Estrategia: iteración hasta punto fijo. En cada pasada se recorren las reglas aún no
        evaluadas; una regla se dispara si todos sus antecedentes están en la memoria de trabajo
        y su consecuente es un hecho nuevo. El ciclo termina cuando se alcanza el objetivo
        (éxito) o cuando una pasada completa no agrega hechos (punto fijo, fallo).
        """
        self.memoria_trabajo = set(hechos_iniciales)
        self.traza_explicacion = []
        derivados = []  # hechos nuevos, en el orden en que se dedujeron

        # Caso base: el objetivo ya es un hecho observado.
        if objetivo in self.memoria_trabajo:
            self.traza_explicacion.append(
                f"'{objetivo}' ya está en los hechos iniciales: no se requiere inferencia.")
            return True

        pendientes = list(self.reglas)  # reglas que todavía no se han evaluado
        hubo_cambio = True
        while hubo_cambio:
            hubo_cambio = False
            for regla in list(pendientes):  # copia: se modifica 'pendientes' dentro del ciclo
                if not regla.antecedentes <= self.memoria_trabajo:
                    continue  # aún faltan antecedentes; se reintenta en la siguiente pasada
                # Con todos sus antecedentes presentes la regla se evalúa una sola vez:
                # los hechos nunca se retiran, así que su resultado no cambiará.
                pendientes.remove(regla)
                if regla.consecuente in self.memoria_trabajo:
                    continue  # no aporta nada nuevo; no se registra como disparo
                self.memoria_trabajo.add(regla.consecuente)
                derivados.append(regla.consecuente)
                self.traza_explicacion.append(f"Paso {len(derivados)}: {self._texto_regla(regla)}")
                hubo_cambio = True
                if regla.consecuente == objetivo:
                    self.traza_explicacion.append(
                        f"Objetivo '{objetivo}' alcanzado en {len(derivados)} pasos.")
                    return True

        # Punto fijo: ninguna regla produce hechos nuevos y el objetivo no apareció.
        self.traza_explicacion.append(
            f"Punto fijo: no se pueden inferir más hechos y '{objetivo}' no fue derivado.")
        self.traza_explicacion.append(
            "Hechos derivados: " + (", ".join(derivados) if derivados else "ninguno"))
        return False

    def ejecutar_inferencia_atras(self, hechos_iniciales, objetivo):
        """
        Motor de Encadenamiento hacia Atrás (Backward Chaining).
        Retorna True si el objetivo puede ser probado, False en caso contrario.

        Estrategia: búsqueda recursiva dirigida por el objetivo (goal-driven). Para probar una
        meta se busca alguna regla que la concluya y se intenta probar todos sus antecedentes
        como sub-metas (AND); si una regla falla se prueba la siguiente (OR).

        Casos base de la recursión (en este orden):
          1. La meta es un hecho inicial            -> True
          2. La meta ya fue demostrada antes        -> True  (memoización de éxitos)
          3. La meta ya se sabe no demostrable      -> False (memoización de fallos)
          4. La meta ya está en la ruta actual      -> False (ciclo; evita bucles infinitos)
          5. Se alcanzó la profundidad máxima       -> False (control de profundidad)
          6. Ninguna regla concluye la meta         -> False
        """
        hechos = set(hechos_iniciales)
        self.traza_explicacion = []

        # Índice consecuente -> reglas que lo concluyen (evita recorrer toda la KB por sub-meta).
        indice = {}
        for regla in self.reglas:
            indice.setdefault(regla.consecuente, []).append(regla)

        probados = set()    # sub-metas demostradas
        fallidos = set()    # sub-metas sin demostración posible
        justificacion = {}  # sub-meta -> regla con la que se demostró (para reconstruir la prueba)
        cortes = [0]        # veces que se cortó una rama por ciclo o por profundidad

        def probar(meta, ruta, nivel):
            sangria = "  " * nivel
            # ---- Casos base ----
            if meta in hechos:
                self.traza_explicacion.append(f"{sangria}[OK] '{meta}' es un hecho inicial")
                return True
            if meta in probados:
                self.traza_explicacion.append(f"{sangria}[OK] '{meta}' ya fue demostrado antes")
                return True
            if meta in fallidos:
                self.traza_explicacion.append(f"{sangria}[X] '{meta}' ya se sabe no demostrable")
                return False
            if meta in ruta:
                cortes[0] += 1
                self.traza_explicacion.append(
                    f"{sangria}[X] ciclo: '{meta}' ya está en la ruta de demostración")
                return False
            if nivel >= self.PROFUNDIDAD_MAXIMA:
                cortes[0] += 1
                self.traza_explicacion.append(
                    f"{sangria}[X] profundidad máxima ({self.PROFUNDIDAD_MAXIMA}) alcanzada en '{meta}'")
                return False
            reglas_meta = indice.get(meta, [])
            if not reglas_meta:
                self.traza_explicacion.append(
                    f"{sangria}[X] '{meta}' no es un hecho inicial y ninguna regla lo concluye")
                fallidos.add(meta)
                return False

            # ---- Paso recursivo ----
            self.traza_explicacion.append(f"{sangria}Meta '{meta}'")
            marca = cortes[0]
            for regla in reglas_meta:
                # Se prueban primero los antecedentes ya observados (fallan o aciertan al instante).
                orden = sorted(regla.antecedentes, key=lambda a: (a not in hechos, a))
                self.traza_explicacion.append(f"{sangria}  Regla {self._texto_regla(regla, orden)}")
                if all(probar(a, ruta | {meta}, nivel + 1) for a in orden):
                    probados.add(meta)
                    justificacion[meta] = regla
                    self.traza_explicacion.append(
                        f"{sangria}[OK] '{meta}' demostrado con {regla.id_regla}")
                    return True
            self.traza_explicacion.append(f"{sangria}[X] '{meta}' no pudo demostrarse")
            # Un fallo solo se memoriza si no dependió de una rama cortada por ciclo/profundidad.
            if cortes[0] == marca:
                fallidos.add(meta)
            return False

        exito = probar(objetivo, frozenset(), 0)

        if exito:
            # Reconstrucción de la prueba: recorrido en post-orden (de los hechos hacia el objetivo).
            orden_prueba, vistos = [], set()

            def reunir(meta):
                if meta in hechos or meta in vistos:
                    return
                vistos.add(meta)
                regla = justificacion[meta]
                for a in sorted(regla.antecedentes):
                    reunir(a)
                orden_prueba.append(regla.id_regla)

            reunir(objetivo)
            if orden_prueba:
                self.traza_explicacion.append(
                    "Prueba (de hechos a objetivo): " + " -> ".join(orden_prueba))
        else:
            self.traza_explicacion.append(
                f"No se pudo demostrar '{objetivo}' a partir de los hechos dados.")
        return exito


# ==========================================================
# PARTE 3: EJECUCIÓN (PUEDEN MODIFICAR PARA PRUEBAS)
# ==========================================================
RUTA_KB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_conocimiento.json")

CASOS_CLINICOS = [
    {
        "id": "caso1",
        "nombre": "Caso 1 - COVID-19 con hipoxemia",
        "sintomas": ["Fiebre", "Escalofrios", "Dolor_Muscular", "Fatiga", "Perdida_Olfato",
                     "Dificultad_Respiratoria", "Saturacion_Oxigeno_Baja"],
        "objetivo": "Alerta_COVID_Grave",
    },
    {
        "id": "caso2",
        "nombre": "Caso 2 - Dengue con signos de alarma e hipotensión",
        "sintomas": ["Fiebre", "Dolor_Cabeza", "Dolor_Detras_Ojos", "Dolor_Articular_Intenso",
                     "Zona_Endemica_Dengue", "Vomito_Persistente", "Dolor_Abdominal_Intenso",
                     "Hipotension"],
        "objetivo": "Alerta_Dengue_Grave",
    },
    {
        "id": "caso3",
        "nombre": "Caso 3 - Neumonía bacteriana grave en paciente de riesgo",
        "sintomas": ["Fiebre", "Escalofrios", "Tos_Productiva", "Esputo_Purulento",
                     "Dolor_Pecho_Pleuritico", "Dificultad_Respiratoria", "Grupo_Riesgo",
                     "Saturacion_Oxigeno_Baja"],
        "objetivo": "Alerta_Neumonia_Grave",
    },
    {
        "id": "caso4a",
        "nombre": "Caso 4a - Mismo síndrome gripal: hecho diferenciador de gripe (objetivo alcanzable)",
        "sintomas": ["Fiebre", "Escalofrios", "Dolor_Muscular", "Fatiga", "Inicio_Brusco", "Grupo_Riesgo"],
        "objetivo": "Indicacion_Antiviral_Influenza",
    },
    {
        "id": "caso4b",
        "nombre": "Caso 4b - Mismo paciente, hipótesis COVID-19 (sin hecho diferenciador: objetivo no derivable)",
        "sintomas": ["Fiebre", "Escalofrios", "Dolor_Muscular", "Fatiga", "Inicio_Brusco", "Grupo_Riesgo"],
        "objetivo": "COVID19",
    },
]


def ejecutar_caso(motor, caso, exportar=False):
    """Corre un caso con ambos motores, imprime resultados y trazas y verifica que coincidan."""
    print("=" * 70)
    print(caso["nombre"])
    print(f"Síntomas iniciales: {caso['sintomas']}")
    print(f"Objetivo a verificar: {caso['objetivo']}\n")

    print("--- Motor Hacia Adelante ---")
    adelante = motor.ejecutar_inferencia(caso["sintomas"], caso["objetivo"])
    print(motor.exportar_traza(f"trazas/{caso['id']}_adelante.txt" if exportar else None))
    print(f"¿Es consecuencia lógica?: {adelante}\n")

    print("--- Motor Hacia Atrás ---")
    atras = motor.ejecutar_inferencia_atras(caso["sintomas"], caso["objetivo"])
    print(motor.exportar_traza(f"trazas/{caso['id']}_atras.txt" if exportar else None))
    print(f"¿Es demostrable?: {atras}")
    print(f"Ambos motores coinciden: {adelante == atras}\n")
    return adelante, atras


if __name__ == "__main__":
    exportar = "--exportar" in sys.argv  # guarda cada traza en trazas/<caso>_<motor>.txt
    if exportar:
        os.makedirs("trazas", exist_ok=True)

    # 1. Inicializar el motor con el archivo de reglas
    motor = MotorInferencia(RUTA_KB)
    print("--- Sistema Experto de Diagnóstico ---")
    print(f"Reglas cargadas: {len(motor.reglas)}\n")

    # 2. Ejecutar los casos clínicos con los dos motores
    for caso in CASOS_CLINICOS:
        ejecutar_caso(motor, caso, exportar)
