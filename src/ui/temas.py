"""
Temas de las tarjetas (Opciones A, B y C del documento de rediseño).

Cómo funciona: cada TaskCard lleva dos propiedades dinámicas de Qt:
    tema -> "clasico" | "categoria" | "pastel"
    cat  -> índice de color de su lista ((categoria_id - 1) % N_COLORES)
generar_qss_temas() produce las reglas [tema="..."][cat="..."] para TODOS los temas y
main.py las agrega al final de estilos.qss. Cambiar de tema = cambiar la propiedad
de las tarjetas y redibujar la grilla; no hace falta recargar la hoja de estilos.

El tema "clasico" no genera reglas: es el que ya está definido en estilos.qss.
"""
from PyQt6.QtCore import QSettings

N_COLORES = 6          # cantidad de colores de lista distintos (índice = (categoria_id - 1) % N_COLORES)
FONDO_VENTANA = "#10242f"

TEMAS = {
    "clasico": {
        "nombre": "Clásico (lima)",
        "descripcion": "Superficie oscura con borde lima. Completadas apagadas.",
    },
    "categoria": {
        "nombre": "Color por lista",
        "descripcion": "Cada lista tiene su propio color de tarjeta.",
    },
    "pastel": {
        "nombre": "Pastel",
        "descripcion": "Tonos pastel con texto oscuro; las hechas pasan a gris azulado.",
    },
}
TEMA_POR_DEFECTO = "clasico"

# (color de borde, color de fondo oscuro) por índice de lista
PALETA_CATEGORIA = [
    ("#B2FA5C", "#1B3340"),  # lima: la lista por defecto ("Tareas") conserva el look clásico
    ("#5CE1FA", "#12343d"),  # cian
    ("#FAA65C", "#3a2c1b"),  # durazno
    ("#FA5C9B", "#3a1b2a"),  # rosa
    ("#A78BFA", "#2a2447"),  # violeta
    ("#FAE15C", "#38341a"),  # amarillo
]
PALETA_PASTEL = ["#CDB4FF", "#FFCBA4", "#B5EAD7"]  # lila, durazno, menta (se repiten cada 3 listas)
TINTA_PASTEL = "#1c1c26"                            # texto y bordes oscuros sobre pastel


def _mezclar(color_a: str, color_b: str, t: float) -> str:
    """Interpola dos colores '#rrggbb'. t=0 devuelve a, t=1 devuelve b."""
    a = [int(color_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(color_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def generar_qss_temas() -> str:
    """Arma el QSS de los temas "categoria" y "pastel" a partir de las paletas."""
    reglas = []
    carta = 'QFrame#task_card'

    # ---------- Tema "categoria": un color por lista ----------
    for i, (borde, fondo) in enumerate(PALETA_CATEGORIA):
        sel = f'{carta}[tema="categoria"][cat="{i}"]'
        fondo_hover = _mezclar(fondo, "#ffffff", 0.07)
        borde_apagado = _mezclar(borde, "#6b7f8a", 0.55)           # desaturado hacia gris
        fondo_apagado = _mezclar(fondo, FONDO_VENTANA, 0.55)
        reglas += [
            f'{sel} {{ background-color: {fondo}; border: 2px solid {borde}; }}',
            f'{sel}:hover {{ background-color: {fondo_hover}; }}',
            f'{sel}[completada="true"] {{ background-color: {fondo_apagado}; border: 2px solid {borde_apagado}; }}',
            f'{sel}[completada="true"]:hover {{ background-color: {fondo}; }}',
            f'{sel} QPushButton#task_check {{ border: 2px solid {borde}; }}',
            f'{sel} QPushButton#task_check:checked {{ background-color: {borde}; }}',
        ]

    # ---------- Tema "pastel": pendientes pastel con tinta oscura; hechas gris azulado ----------
    for i in range(N_COLORES):
        pastel = PALETA_PASTEL[i % len(PALETA_PASTEL)]
        sel = f'{carta}[tema="pastel"][cat="{i}"][completada="false"]'
        reglas += [
            f'{sel} {{ background-color: {pastel}; border: 2px solid {TINTA_PASTEL}; }}',
            f'{sel}:hover {{ background-color: {_mezclar(pastel, "#ffffff", 0.35)}; }}',
        ]

    pend = f'{carta}[tema="pastel"][completada="false"]'
    hecha = f'{carta}[tema="pastel"][completada="true"]'
    reglas += [
        f'{pend} QLabel#task_desc {{ color: {TINTA_PASTEL}; }}',
        f'{pend} QLabel#task_id_label {{ color: #4a4a63; }}',
        f'{pend} QPushButton#task_check {{ border: 2px solid {TINTA_PASTEL}; }}',
        f'{pend} QPushButton#task_check:hover {{ color: rgba(28, 28, 38, 110); }}',
        f'{pend} QPushButton#task_menu {{ color: {TINTA_PASTEL}; }}',
        f'{hecha} {{ background-color: #2c3e4a; border: 2px solid #43606f; }}',
        f'{hecha}:hover {{ background-color: #33495a; }}',
    ]
    return "\n/* --- Temas generados por ui/temas.py --- */\n" + "\n".join(reglas) + "\n"


# ---------- Persistencia (QSettings: archivo/registro propio del SO, sin tocar la base de datos) ----------
def _settings() -> QSettings:
    return QSettings("ToDoApp", "ToDoApp")


def cargar_tema() -> str:
    """Devuelve el último tema elegido; si no hay uno guardado (o es inválido), el clásico."""
    tema = _settings().value("tema", TEMA_POR_DEFECTO)
    return tema if tema in TEMAS else TEMA_POR_DEFECTO


def guardar_tema(tema: str):
    _settings().setValue("tema", tema)
