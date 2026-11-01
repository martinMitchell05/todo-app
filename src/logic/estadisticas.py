"""
Lógica pura del panel de progreso (sin PyQt): recibe el diccionario que arma
Database.obtener_estadisticas() y devuelve texto listo para mostrar.
"""


def barra_progreso(hechas: int, total: int, ancho: int = 10) -> str:
    """
    Barra de caracteres estilo terminal: [██████░░░░] 6/10.
    Se redondea hacia abajo para que la barra solo se llene del todo cuando de verdad
    está todo completo, pero se garantiza al menos un bloque si ya hay algo hecho.
    """
    llenos = 0 if total == 0 else int(ancho * hechas / total)
    if hechas > 0 and llenos == 0:
        llenos = 1
    return f"[{'█' * llenos}{'░' * (ancho - llenos)}] {hechas}/{total}"


def armar_datos_curiosos(stats: dict) -> list:
    """
    Devuelve una lista de frases con datos curiosos para rotar en la UI. Nunca queda
    vacía (con la base vacía devuelve un consejo). En empates gana la lista más
    antigua, porque max() devuelve el primer máximo que encuentra.
    """
    total, hechas, cats = stats["total"], stats["completadas"], stats["categorias"]
    if total == 0:
        return ["💡 Todavía no hay tareas: anotá la primera arriba."]

    datos = [f"🎯 Completaste el {round(100 * hechas / total)}% de todo lo que anotaste."]

    con_tareas = [c for c in cats if c["total"] > 0]
    if con_tareas:
        top = max(con_tareas, key=lambda c: c["total"])
        datos.append(f"📂 La lista con más tareas es «{top['nombre']}» ({top['total']}).")

    if hechas > 0:
        top = max(con_tareas, key=lambda c: c["completadas"])
        datos.append(
            f"🏆 La lista con más completadas es «{top['nombre']}» "
            f"({top['completadas']} de {top['total']})."
        )
        al_dia = max(con_tareas, key=lambda c: c["completadas"] / c["total"])
        datos.append(
            f"🔥 La lista más al día es «{al_dia['nombre']}» "
            f"({round(100 * al_dia['completadas'] / al_dia['total'])}% hecho)."
        )
    return datos
