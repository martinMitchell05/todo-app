from PyQt6.QtGui import QColor
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QPointF, QPoint,
    QSequentialAnimationGroup, QPauseAnimation,
)
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QFrame,
    QScrollArea,
    QButtonGroup,
    QInputDialog,
    QMessageBox,
    QMenu,
    QSizePolicy,
)
from logic.database import Database
from logic.estadisticas import barra_progreso, armar_datos_curiosos
from ui.temas import N_COLORES, cargar_tema, guardar_tema
from ui.dialogo_temas import DialogoTemas

# --- Constantes de diseño (un solo lugar para ajustar la grilla y el "feel" de las tarjetas) ---
MAX_COLUMNAS = 3
CARD_ANCHO, CARD_ALTO = 220, 170

# Offsets (x, y) de la sombra dura según el estado de la tarjeta. Cuanto más grande
# el offset, más "levantada" parece; la presionada casi pega la sombra a la tarjeta.
SOMBRA_REPOSO = QPointF(4.0, 6.0)
SOMBRA_HOVER = QPointF(6.0, 10.0)
SOMBRA_PRESIONADA = QPointF(1.0, 2.0)

# Completar con gracia: pausa (para que se vea el tachado) + fade de salida/entrada, en ms
PAUSA_TACHADO_MS = 140
FADE_MS = 200


class TaskCard(QFrame):
    def __init__(self, task_id, descripcion, completada, categoria_id, main_window, entrada_animada=False):
        super().__init__()
        self.task_id = task_id
        self.descripcion = descripcion
        self.completada = completada  # se guarda para poder pasarlo al abrir el detalle
        self.categoria_id = categoria_id  # lista a la que pertenece (para el tema por color y el menú "Mover a...")
        self.main_window = main_window

        self.setObjectName("task_card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self.descripcion)  # la tarjeta es de tamaño fijo: el tooltip muestra el texto completo

        # Propiedades dinámicas que leen los selectores de estilos.qss / ui/temas.py.
        # Se setean ANTES de mostrar el widget, así el primer "polish" ya las lee.
        self.setProperty("tema", main_window.tema_actual)
        # (id - 1): la lista por defecto ("Tareas", id 1) cae en el índice 0 = lima, el look clásico
        self.setProperty("cat", str((categoria_id - 1) % N_COLORES))

        # Layout: [ check | descripción | ⋮ ] arriba, "Tarea #N" abajo como metadato chico
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        fila_superior = QHBoxLayout()
        fila_superior.setSpacing(10)

        # Checkbox "brutalista": QPushButton checkable (se estiliza 100% por QSS, sin imágenes)
        self.check_button = QPushButton("✓")
        self.check_button.setObjectName("task_check")
        self.check_button.setCheckable(True)
        self.check_button.setChecked(completada)  # setChecked NO emite clicked, solo toggled
        self.check_button.setFixedSize(26, 26)
        self.check_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.check_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_button.clicked.connect(self._al_tildar)
        fila_superior.addWidget(self.check_button, 0, Qt.AlignmentFlag.AlignTop)

        self.desc_label = QLabel(self.descripcion)
        self.desc_label.setObjectName("task_desc")
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        fila_superior.addWidget(self.desc_label, 1)

        # Menú contextual ⋮: aparece solo en hover (ver enterEvent/leaveEvent).
        # retainSizeWhenHidden reserva su lugar aunque esté oculto; si no, el texto
        # de la descripción se reacomodaría cada vez que pasás el mouse por la tarjeta.
        self.menu_button = QPushButton("⋮")
        self.menu_button.setObjectName("task_menu")
        self.menu_button.setFixedSize(22, 26)
        self.menu_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.menu_button.setCursor(Qt.CursorShape.PointingHandCursor)
        politica = self.menu_button.sizePolicy()
        politica.setRetainSizeWhenHidden(True)
        self.menu_button.setSizePolicy(politica)
        self.menu_button.clicked.connect(lambda: self.main_window.mostrar_menu_tarea(self, self.menu_button))
        fila_superior.addWidget(self.menu_button, 0, Qt.AlignmentFlag.AlignTop)
        self.menu_button.setVisible(False)

        layout.addLayout(fila_superior)
        layout.addStretch()  # empuja el pie hacia abajo, sin importar cuánto texto tenga la descripción

        # Pie de la tarjeta. A la derecha queda lugar libre para la "píldora" de
        # fecha de vencimiento (todavía no hay columna en la DB).
        id_label = QLabel(f"Tarea #{self.task_id}")
        id_label.setObjectName("task_id_label")
        id_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(id_label)

        self._aplicar_estado_visual(completada)
        self.setFixedSize(CARD_ANCHO, CARD_ALTO)

        if entrada_animada:
            self._aparecer()  # la tarjeta que acaba de cambiar de bloque entra con un fade-in
        else:
            self.main_window.aplicar_sombra_dura(self)

    # ---------- Estado visual ----------
    def _aplicar_estado_visual(self, completada, repintar=False):
        """
        Sincroniza la propiedad dinámica "completada" de la tarjeta y de su texto
        (los selectores [completada="true"] del QSS hacen el resto: colores y tachado).
        Qt NO re-evalúa el QSS solo porque cambió una propiedad en caliente: con
        repintar=True se hace unpolish()/polish() para que se aplique de inmediato.
        """
        valor = "true" if completada else "false"
        self.setProperty("completada", valor)
        self.desc_label.setProperty("completada", valor)
        if repintar:
            for w in (self, self.desc_label):
                w.style().unpolish(w)
                w.style().polish(w)

    # ---------- Completar con gracia ----------
    def _al_tildar(self, checked):
        """
        Slot del checkbox (`checked` = estado NUEVO). Secuencia:
        1) feedback inmediato: tachado/apagado al instante; 2) pausa corta para que se vea;
        3) fade-out; 4) recién ahí se persiste y se redibuja (MainWindow.toggle_completada_card),
        y la tarjeta reaparece en su bloque nuevo con fade-in.
        Nota: el tachado es instantáneo, no un trazo animado (QLabel no puede animar un tachado parcial).
        """
        self.check_button.setEnabled(False)  # evita doble click durante la animación
        self._aplicar_estado_visual(checked, repintar=True)
        self.main_window.preparar_entrada_animada(self.task_id)

        # QGraphicsOpacityEffect reemplaza a la sombra: Qt permite un solo efecto por widget
        efecto = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(efecto)
        fade = QPropertyAnimation(efecto, b"opacity")
        fade.setDuration(FADE_MS)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)

        # El grupo vive en self: si la tarjeta se destruye antes de terminar, la animación se va con ella
        self.anim_salida = QSequentialAnimationGroup(self)
        self.anim_salida.addAnimation(QPauseAnimation(PAUSA_TACHADO_MS))
        self.anim_salida.addAnimation(fade)
        self.anim_salida.finished.connect(lambda: self.main_window.toggle_completada_card(self.task_id, checked))
        self.anim_salida.start()

    def _aparecer(self):
        """Fade-in de entrada; al terminar devuelve la sombra dura (que reemplaza al efecto de opacidad)."""
        efecto = QGraphicsOpacityEffect(self)
        efecto.setOpacity(0.0)
        self.setGraphicsEffect(efecto)
        self.anim_entrada = QPropertyAnimation(efecto, b"opacity", self)
        self.anim_entrada.setDuration(FADE_MS)
        self.anim_entrada.setStartValue(0.0)
        self.anim_entrada.setEndValue(1.0)
        self.anim_entrada.finished.connect(lambda: self.main_window.aplicar_sombra_dura(self))
        self.anim_entrada.start()

    # ---------- Sombra y mouse ----------
    def _animar_sombra(self, destino: QPointF, duracion_ms: int):
        """
        Anima el offset de la sombra dura hasta `destino`. Simula que la tarjeta
        "sube" o se "hunde": la geometría real la maneja el QGridLayout (mover el
        widget a mano se pisaría en el próximo relayout), así que lo que se mueve
        es la sombra. Necesita que la tarjeta tenga un QGraphicsDropShadowEffect
        (lo asigna MainWindow.aplicar_sombra_dura); si no lo tiene (por ejemplo,
        durante un fade) no hace nada.
        """
        efecto = self.graphicsEffect()
        if not isinstance(efecto, QGraphicsDropShadowEffect):
            return
        # Se guarda en self para que Python no destruya la animación mientras corre
        self.anim_shadow = QPropertyAnimation(efecto, b"offset")
        self.anim_shadow.setDuration(duracion_ms)
        self.anim_shadow.setStartValue(efecto.offset())
        self.anim_shadow.setEndValue(destino)
        self.anim_shadow.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim_shadow.start()

    def enterEvent(self, event):
        """Hover in: la sombra crece y aparece el menú ⋮."""
        self._animar_sombra(SOMBRA_HOVER, 150)
        self.menu_button.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hover out: la sombra vuelve a reposo y se oculta el menú ⋮."""
        self._animar_sombra(SOMBRA_REPOSO, 150)
        self.menu_button.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """
        Al presionar, la tarjeta se "hunde" (sombra casi pegada). El detalle se abre
        recién al SOLTAR (mouseReleaseEvent), como en un botón real.
        Ojo: acá NO se llama a super(): la implementación base de QWidget ignora el
        evento, y un press ignorado se delega al padre -> esta tarjeta nunca
        recibiría el release.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._animar_sombra(SOMBRA_PRESIONADA, 60)
        event.accept()

    def mouseReleaseEvent(self, event):
        """Abre el detalle solo si el click se soltó DENTRO de la tarjeta (permite arrepentirse arrastrando afuera)."""
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self._animar_sombra(SOMBRA_HOVER, 100)
            self.main_window.abrir_detalle_tarea_card(self.task_id, self.descripcion, self.completada)
        event.accept()


class DetailWindow(QWidget):
    def __init__(self, task_id, task_desc, completada, db_connection, refresh_callback):
        super().__init__()
        self.task_id = task_id
        self.completada = completada
        self.db = db_connection
        self.refresh_callback = refresh_callback # Función para recargar la lista principal

        self.setObjectName("detail_window")
        self.setWindowTitle(f"Detalle de Tarea #{self.task_id}")
        self.resize(440, 340)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # --- Badge de estado: se repinta solo (ver actualizar_estado_visual) ---
        self.estado_label = QLabel()
        self.estado_label.setObjectName("estado_label")
        self.estado_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.estado_label)

        # --- Descripción editable ---
        self.label_desc = QLabel(f"Tarea #{self.task_id}")
        self.label_desc.setObjectName("label_desc")
        self.label_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_desc)

        self.desc_input = QLineEdit(task_desc)
        self.desc_input.setObjectName("desc_input")
        layout.addWidget(self.desc_input)

        self.save_button = QPushButton("💾  Guardar Cambios")
        self.save_button.setObjectName("save_button")
        layout.addWidget(self.save_button)

        layout.addStretch()  # separa la acción principal (guardar) de las secundarias de abajo

        # --- Acciones secundarias, agrupadas en una fila: completar/desmarcar + eliminar ---
        acciones_layout = QHBoxLayout()
        acciones_layout.setSpacing(10)

        self.complete_button = QPushButton()  # el texto lo pone actualizar_estado_visual()
        self.complete_button.setObjectName("complete_button")
        acciones_layout.addWidget(self.complete_button)

        self.delete_button = QPushButton("Eliminar")
        self.delete_button.setObjectName("delete_button")
        acciones_layout.addWidget(self.delete_button)

        layout.addLayout(acciones_layout)

        self.actualizar_estado_visual()  # pinta el badge y el botón según self.completada, ANTES de mostrar la ventana

        self.save_button.clicked.connect(self.guardar_cambios)
        self.complete_button.clicked.connect(self.toggle_completada)
        self.delete_button.clicked.connect(self.eliminar_tarea)

    def actualizar_estado_visual(self):
        """
        Sincroniza el badge de estado y el texto del botón con self.completada.
        setProperty() define una "propiedad dinámica" de Qt (no existe en QLabel
        de fábrica); estilos.qss la usa como selector: QLabel#estado_label[completada="true"].
        Qt NO re-evalúa el QSS solo porque cambiaste una propiedad en caliente —
        hay que "despintar y repintar" el widget con unpolish()/polish() para que
        el estilo nuevo se aplique de una.
        """
        if self.completada:
            self.estado_label.setText("✅  Completada")
            self.estado_label.setProperty("completada", "true")
            self.complete_button.setText("Pendiente")
        else:
            self.estado_label.setText("🕓  Pendiente")
            self.estado_label.setProperty("completada", "false")
            self.complete_button.setText("Completada")

        self.estado_label.style().unpolish(self.estado_label)
        self.estado_label.style().polish(self.estado_label)

    def guardar_cambios(self):
        nueva_desc = self.desc_input.text().strip()
        if nueva_desc:
            self.db.actualizar_descripcion(self.task_id, nueva_desc)
            self.refresh_callback() # Le avisa a la ventana principal que actualice la lista
            self.close() # Cierra la ventana de detalle

    def toggle_completada(self):
        """
        Un solo botón para las dos direcciones: si está completada la desmarca,
        si está pendiente la marca. A diferencia de guardar_cambios/eliminar_tarea,
        NO cierra la ventana — así podés togglear varias veces sin tener que
        reabrir el detalle cada vez.
        """
        if self.completada:
            self.db.desmarcar_como_completada(self.task_id)
        else:
            self.db.marcar_como_completada(self.task_id)

        self.completada = not self.completada
        self.actualizar_estado_visual()
        self.refresh_callback()  # refresca la grilla de fondo (para ver el tachado) sin cerrar este panel

    def eliminar_tarea(self):
        self.db.eliminar_tarea(self.task_id)
        self.refresh_callback()
        self.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración básica de la ventana
        self.setWindowTitle(" --- To-Do App | Personal --- ")
        self.resize(1100, 700) # Ancho, Alto inicial
        self.db = Database() # Inicializa la base de datos al iniciar la aplicación
        self.detail_window = None  # Ventana de detalle de tarea
        self.categoria_actual = None  # None = "Todas las tareas" (sin filtro de lista)
        self.completadas_colapsadas = False  # estado del separador "-- Completadas (N) --"
        self.tema_actual = cargar_tema()     # "clasico" | "categoria" | "pastel" (persistido con QSettings)
        self.datos_curiosos = []             # frases del panel de progreso (las arma actualizar_stats)
        self.indice_dato = 0                 # cuál de esas frases se muestra ahora
        self._tarea_recien_movida = None     # id de la tarjeta que debe entrar con fade-in tras redibujar

        # 1. Widget central (Obligatorio en QMainWindow)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 2. Layout raíz: horizontal -> [ sidebar | contenido ]
        root_layout = QHBoxLayout(self.central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ---------- Sidebar (navegación) ----------
        sidebar = self.crear_sidebar()
        root_layout.addWidget(sidebar)

        # ---------- Contenido principal  ----------
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 16, 24, 16)
        root_layout.addWidget(content_widget, 1)  # stretch=1: se lleva todo el ancho restante

        header = self.crear_header()
        content_layout.addWidget(header)
        content_layout.addWidget(self.crear_panel_stats())

        grid_layout = QGridLayout()

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Qué hay que hacer hoy?")
        self.task_input.setObjectName("task_input")
        self.aplicar_sombra_suave(self.task_input)

        self.tasks_button = QPushButton("Ver Tareas")
        self.tasks_button.setObjectName("tasks_button")
        self.aplicar_sombra_dura(self.tasks_button)

        self.clear_button = QPushButton("Limpiar vista")
        self.clear_button.setObjectName("clear_button")
        self.aplicar_sombra_dura(self.clear_button)

        # Fila 0, Columna 0: Botón "Actualizar"
        grid_layout.addWidget(self.tasks_button, 0, 0)
        # Fila 0, Columnas 1-4: El input
        grid_layout.addWidget(self.task_input, 0, 1, 1, 4)
        # Fila 0, Columna 6: Botón "Limpiar vista"
        grid_layout.addWidget(self.clear_button, 0, 6)

        content_layout.addLayout(grid_layout)

        self.setStatusBar(QStatusBar(self))

        # --- Área de scroll y matriz de tareas (tarjetas) ---
        # El fondo/borde del scroll se define en estilos.qss (QScrollArea#scroll_tareas).
        # Antes iba como setStyleSheet() inline SIN selector: se propagaba a todos los
        # descendientes y anulaba el borde y el fondo de las tarjetas definidos en el QSS.
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("scroll_tareas")
        self.scroll_area.setWidgetResizable(True)

        # Contenedor interno donde van a ir las tarjetas
        self.tasks_container = QWidget()
        self.tasks_container.setObjectName("tasks_container")
        self.scroll_area.setWidget(self.tasks_container)

        # La grilla que ordenará las tarjetas
        self.tasks_grid = QGridLayout(self.tasks_container)
        self.tasks_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        self.tasks_grid.setSpacing(16)  # espacio entre tarjetas
        # Ancho mínimo por columna = ancho de tarjeta: así el separador (que ocupa las
        # 3 columnas) mide siempre lo mismo, haya 1 o 3 tarjetas en la fila.
        for columna in range(MAX_COLUMNAS):
            self.tasks_grid.setColumnMinimumWidth(columna, CARD_ANCHO)

        content_layout.addWidget(self.scroll_area, 1)  # stretch=1: se lleva todo el alto restante


        # Conectar Señales a Slots (Funciones)
        self.tasks_button.clicked.connect(self.obtener_tareas)
        # Esto permite agregar la tarea apretando "Enter"
        self.task_input.returnPressed.connect(self.agregar_tarea_ui)
        self.clear_button.clicked.connect(self.limpiar_lista)
        self.filter_button.toggled.connect(self.obtener_tareas)

        # Cargar las tareas existentes apenas arranca la app
        self.obtener_tareas()


    def crear_sidebar(self) -> QFrame:
        """
        Arma el panel lateral de navegación (izquierda). Tiene dos partes distintas:
        - Secciones placeholder (Dashboard, Calendario, Etiquetas, Configuración):
          puramente visuales, para cuando el proyecto crezca.
        - Sección "LISTAS": las categorías reales del usuario, cargadas desde la base
          de datos vía poblar_categorias(). "Todas las tareas" es la única que no
          vive en la tabla `categorias` — es la vista sin filtro (categoria_id=None).
        Devuelve el QFrame listo para insertar en el layout raíz.
        """
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 24, 0, 24)
        layout.setSpacing(4)

        logo = QLabel(" -- To-Do App -- ")
        logo.setObjectName("logo_label")
        layout.addWidget(logo)
        layout.addSpacing(16)

        # QButtonGroup asegura que solo una sección quede "activa" (checked) a la vez
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        secciones = [
            ("🏠  Dashboard", False),
            ("📅  Calendario", False),
            ("🏷️  Etiquetas", False),
            ("⚙️  Configuración", False),
        ]
        for texto, activo in secciones:
            boton = QPushButton(texto)
            boton.setObjectName("nav_button")
            boton.setCheckable(True)
            boton.setChecked(activo)
            boton.clicked.connect(self.seleccionar_seccion)
            self.nav_group.addButton(boton)
            layout.addWidget(boton)

        # ---------- Listas ----------
        layout.addSpacing(14)

        listas_header = QLabel("LISTAS")
        listas_header.setObjectName("sidebar_section_label")
        layout.addWidget(listas_header)

        # Contenedor vacío: poblar_categorias() lo llena (y lo vuelve a llenar
        # cada vez que se crea una lista nueva)
        
        self.scroll_area_categorias = QScrollArea()
        self.scroll_area_categorias.setWidgetResizable(True)
        self.scroll_area_categorias.setObjectName("scroll_categorias")

        self.categorias_container = QWidget()
        self.categorias_container.setObjectName("categorias_container")

        self.categorias_layout = QVBoxLayout(self.categorias_container)
        self.categorias_layout.setContentsMargins(0, 0, 0, 0) # sacar márgenes para que quede alineado
        self.categorias_layout.setSpacing(5)
        
        # para que las listas no se estiren y se apilen bien arriba
        self.categorias_layout.setAlignment(Qt.AlignmentFlag.AlignTop) 

        self.scroll_area_categorias.setWidget(self.categorias_container)
        layout.addWidget(self.scroll_area_categorias)
        self.poblar_categorias()

        self.new_list_button = QPushButton("+  Nueva lista")
        self.new_list_button.setObjectName("new_list_button")
        self.new_list_button.clicked.connect(self.crear_categoria_ui)
        layout.addWidget(self.new_list_button)

        layout.addStretch()  # empuja el botón de abajo hasta el fondo del sidebar

        self.new_task_sidebar_button = QPushButton("+  Nueva Tarea")
        self.new_task_sidebar_button.setObjectName("new_task_button")
        self.new_task_sidebar_button.clicked.connect(self.foco_nueva_tarea)
        layout.addWidget(self.new_task_sidebar_button)

        return sidebar

    def poblar_categorias(self):
        """
        (Re)dibuja los botones de listas del sidebar según lo que haya en la base de datos.
        Se llama una vez al armar la ventana (desde crear_sidebar) y cada vez que se
        crea una lista nueva (desde crear_categoria_ui). Necesita self.db (para traer
        las categorías) y self.categoria_actual (para saber cuál marcar como activa).
        """
        # Sacar los botones viejos antes de repoblar (si los hay)
        while self.categorias_layout.count():
            item = self.categorias_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Se recrea en cada llamada: los botones viejos del grupo ya no existen
        self.categoria_group = QButtonGroup(self)
        self.categoria_group.setExclusive(True)

        # "Todas las tareas" no es una fila de 'categorias' — es la vista sin filtro
        boton_todas = QPushButton("🗂️  Todas las tareas")
        boton_todas.setObjectName("nav_button")
        boton_todas.setCheckable(True)
        boton_todas.setChecked(self.categoria_actual is None)
        boton_todas.clicked.connect(lambda: self.seleccionar_categoria(None, "Todas las tareas"))
        self.categoria_group.addButton(boton_todas)
        self.categorias_layout.addWidget(boton_todas)

        for categoria_id, nombre in self.db.obtener_categorias():
            boton = QPushButton(f"📑  {nombre}")
            boton.setObjectName("nav_button")
            boton.setCheckable(True)
            boton.setChecked(self.categoria_actual == categoria_id)
            # cid=categoria_id y n=nombre "congelan" los valores de esta vuelta del for. Sin el
            # default arg, los lambdas comparten la misma variable del closure, y para cuando
            # los apretás todos valen lo último que tomó el for (closure tardía de Python)
            # -> todos los botones abrirían la última lista.
            boton.clicked.connect(lambda checked, cid=categoria_id, n=nombre: self.seleccionar_categoria(cid, n))
            self.categoria_group.addButton(boton)
            self.categorias_layout.addWidget(boton)

            # Click derecho -> menú con "Eliminar lista". La categoría por defecto
            # ("Tareas") queda afuera a propósito: no se puede borrar (ver eliminar_categoria
            # en database.py)
            if categoria_id != self.db.categoria_default_id:
                boton.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                boton.customContextMenuRequested.connect(
                    lambda punto, b=boton, cid=categoria_id, n=nombre: self.mostrar_menu_categoria(b, cid, n, punto)
                )

    def mostrar_menu_categoria(self, boton, categoria_id, nombre, punto):
        """
        Menú contextual (click derecho) sobre una lista del sidebar. `punto` viene
        en coordenadas locales del botón; mapToGlobal lo convierte a coordenadas de
        pantalla, que es lo que QMenu.exec() necesita para saber dónde dibujarse.
        """
        menu = QMenu(self)
        accion_eliminar = menu.addAction("🗑️  Eliminar lista")
        accion_elegida = menu.exec(boton.mapToGlobal(punto))
        if accion_elegida == accion_eliminar:
            self.eliminar_categoria_ui(categoria_id, nombre)
        

    def seleccionar_categoria(self, categoria_id, nombre="Todas las tareas"):
        """Cambia la lista activa (None = Todas), actualiza el título del header y redibuja la grilla."""
        self.categoria_actual = categoria_id
        self.header_title.setText(nombre)
        self.obtener_tareas()

    def crear_categoria_ui(self):
        """
        Pide el nombre de la lista nueva con el diálogo nativo de Qt.
        QInputDialog.getText() devuelve una tupla (texto, ok); `ok` es False si el
        usuario tocó "Cancelar" — por eso no alcanza con chequear que el texto no esté vacío.
        """
        nombre, ok = QInputDialog.getText(self, "Nueva lista", "Nombre de la lista:")
        nombre = nombre.strip()

        if not ok or not nombre:
            return

        nueva_id = self.db.crear_categoria(nombre)
        self.categoria_actual = nueva_id
        self.header_title.setText(nombre)
        self.poblar_categorias()  # redibuja el sidebar con la lista nueva ya incluida
        self.obtener_tareas()     # muestra su vista (vacía, recién creada)

    def eliminar_categoria_ui(self, categoria_id, nombre):
        """
        Confirma con el usuario y elimina una lista junto con todas sus tareas.
        Muestra la cantidad de tareas que se van a borrar para que la confirmación
        sea informada, no un "¿estás seguro?" genérico.
        """
        cantidad = len(self.db.obtener_tareas(categoria_id))
        respuesta = QMessageBox.question(
            self,
            "Eliminar lista",
            f'¿Eliminar la lista "{nombre}"? Esto borra también su{"s" if cantidad != 1 else ""} '
            f'{cantidad} tarea{"s" if cantidad != 1 else ""} asociada{"s" if cantidad != 1 else ""}. '
            f'Esta acción no se puede deshacer.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,  # botón que queda seleccionado por default (Enter no borra por accidente)
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
 
        self.db.eliminar_categoria(categoria_id)
 
        # Si estabas viendo justo la lista que borraste, volvés a "Todas las tareas"
        if self.categoria_actual == categoria_id:
            self.categoria_actual = None
            self.header_title.setText("Todas las tareas")
 
        self.poblar_categorias()
        self.obtener_tareas()
        

    def crear_header(self) -> QFrame:
        """
        Arma la franja superior del área de contenido: título de la sección actual +
        el botón que filtra tareas completadas. Reemplaza al QToolBar nativo que tenías
        antes, para poder pintarlo con el mismo QSS "brutalista" que el resto de los botones.
        No necesita datos del proyecto; guarda `self.filter_button` porque su señal
        `toggled` se conecta más abajo, en __init__, a filtrar_tareas_completadas.
        """
        header = QFrame()
        header.setObjectName("header")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 12)

        titulo = QLabel("Todas las tareas")
        titulo.setObjectName("header_title")
        self.header_title = titulo
        layout.addWidget(titulo)
        layout.addStretch()

        # Chip informativo: muestra "🕓 pendientes  ✅ completadas" de la lista actual
        # (texto que actualiza obtener_tareas) y sigue siendo el interruptor del filtro
        # "solo completadas".
        self.filter_button = QPushButton("🕓 0   ✅ 0")
        self.filter_button.setObjectName("filter_button")
        self.filter_button.setCheckable(True)
        self.filter_button.setToolTip("Pendientes y completadas de esta lista.\nClick: mostrar solo las completadas.")
        self.filter_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.aplicar_sombra_dura(self.filter_button)
        layout.addWidget(self.filter_button)

        return header

    def seleccionar_seccion(self):
        """
        Handler común para todos los botones de navegación del sidebar.
        self.sender() devuelve el QPushButton concreto que disparó la señal 'clicked';
        así no hace falta un método distinto por cada botón.
        "Configuración" abre el diálogo de temas; el resto sigue siendo placeholder.
        """
        boton = self.sender()
        if "Configuración" in boton.text():
            self.abrir_dialogo_temas()
            # El diálogo es un popup, no una pantalla: se des-marca el botón para que el
            # sidebar no quede resaltado. Un QButtonGroup exclusivo no deja desmarcar,
            # por eso se desactiva la exclusividad un instante.
            self.nav_group.setExclusive(False)
            boton.setChecked(False)
            self.nav_group.setExclusive(True)
        else:
            self.statusBar().showMessage(f"🚧 «{boton.text().strip()}» todavía no está implementado.", 4000)

    def abrir_dialogo_temas(self):
        """Abre Configuración > Temas (modal). Necesita self.tema_actual y self.aplicar_tema."""
        DialogoTemas(self.tema_actual, self.aplicar_tema, self).exec()

    def aplicar_tema(self, tema):
        """
        Guarda el tema elegido y redibuja la grilla: las tarjetas nuevas nacen con la
        propiedad dinámica `tema` actualizada y los selectores de ui/temas.py hacen el resto.
        """
        self.tema_actual = tema
        guardar_tema(tema)
        self.recargar_lista()

    def foco_nueva_tarea(self):
        """Atajo del botón 'Nueva Tarea' del sidebar: lleva el cursor directo al input de alta."""
        self.task_input.setFocus()

    def agregar_tarea_ui(self):
        """
        Toma el texto del input, lo guarda en la base de datos (en la lista activa
        del sidebar) y recarga la matriz visual.
        """
        texto = self.task_input.text().strip() 

        if texto: # Solo agrega si no está vacío
            # self.categoria_actual: la tarea cae en la lista que el usuario tiene
            # abierta; si está en "Todas las tareas" (None), agregar_tarea la manda
            # a la categoría por defecto ("Tareas") — ver database.py
            id = self.db.agregar_tarea(texto, self.categoria_actual)

            if id is not None:  # Verifica que se haya guardado correctamente
                # En lugar de intentar agregar un ítem suelto, redibuja toda la matriz
                self.recargar_lista() 
                
                self.task_input.clear() # Limpia el input para la siguiente tarea
            else:
                self.statusBar().showMessage("!⚠ Error al agregar la tarea a la base de datos.", 5000)


    def obtener_tareas(self):
        """
        Dibuja la grilla: tarjetas pendientes, luego un separador colapsable
        "-- Completadas (N) --" y debajo las completadas. Con el filtro "solo
        completadas" activo se muestran solo estas, sin separador. Si no hay nada
        para mostrar, dibuja el estado vacío. Además refresca el chip del header y
        el panel de progreso.
        Datos que necesita: self.db, self.categoria_actual, self.filter_button y
        self.completadas_colapsadas.
        """
        self.limpiar_lista()
        tareas = self.db.obtener_tareas(self.categoria_actual)
        solo_completadas = self.filter_button.isChecked()

        pendientes = [] if solo_completadas else [t for t in tareas if not t[2]]
        completadas = [t for t in tareas if t[2]]

        fila = self._agregar_tarjetas(pendientes, fila_inicial=0)

        if solo_completadas:
            self._agregar_tarjetas(completadas, fila)
        elif completadas:
            separador = self._crear_separador_completadas(len(completadas))
            self.tasks_grid.addWidget(separador, fila, 0, 1, MAX_COLUMNAS)  # ocupa las 3 columnas
            if not self.completadas_colapsadas:
                self._agregar_tarjetas(completadas, fila + 1)

        # Se decide con las listas, no con tasks_grid.count(): los widgets viejos recién
        # se destruyen al volver al event loop (deleteLater) y seguirían contando.
        if not pendientes and not completadas:
            self.tasks_grid.addWidget(
                self._crear_estado_vacio(solo_completadas), 0, 0, 1, MAX_COLUMNAS,
                Qt.AlignmentFlag.AlignHCenter,
            )

        n_completadas = len(completadas)
        self.filter_button.setText(f"🕓 {len(tareas) - n_completadas}   ✅ {n_completadas}")
        self.actualizar_stats()
        self._tarea_recien_movida = None  # el fade-in es de un solo uso

    def _agregar_tarjetas(self, tareas, fila_inicial) -> int:
        """
        Coloca una TaskCard por cada tupla (id, descripcion, completada) en la grilla,
        de a MAX_COLUMNAS por fila, a partir de `fila_inicial`.
        Cada tupla es (id, descripcion, completada, categoria_id).
        Devuelve la próxima fila libre (techo de len(tareas) / MAX_COLUMNAS), para
        encadenar bloques sin llevar un contador global de tarjetas.
        """
        for i, (id_tarea, descripcion, completada, categoria_id) in enumerate(tareas):
            tarjeta = TaskCard(
                id_tarea, descripcion, completada, categoria_id, self,
                entrada_animada=(id_tarea == self._tarea_recien_movida),
            )
            self.tasks_grid.addWidget(tarjeta, fila_inicial + i // MAX_COLUMNAS, i % MAX_COLUMNAS)
        return fila_inicial + (len(tareas) + MAX_COLUMNAS - 1) // MAX_COLUMNAS

    def _crear_separador_completadas(self, cantidad) -> QPushButton:
        """
        Botón-encabezado que hace de separador y de interruptor de colapso.
        `cantidad` es solo para el texto. La flecha refleja self.completadas_colapsadas.
        """
        flecha = "▸" if self.completadas_colapsadas else "▾"
        boton = QPushButton(f"{flecha}  -- Completadas ({cantidad}) --")
        boton.setObjectName("section_toggle")
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        boton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        boton.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        boton.clicked.connect(self.alternar_completadas)
        return boton

    def crear_panel_stats(self) -> QFrame:
        """
        Franja entre el header y el input: barra de progreso en caracteres (global, todas
        las listas) + un "dato curioso" que rota al hacer click. Guarda `progress_label` y
        `fact_button` porque los actualiza actualizar_stats(). No necesita datos del proyecto
        al construirse.
        """
        panel = QFrame()
        panel.setObjectName("stats_panel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 6)
        layout.setSpacing(16)

        self.progress_label = QLabel()
        self.progress_label.setObjectName("progress_label")
        layout.addWidget(self.progress_label)

        self.fact_button = QPushButton()
        self.fact_button.setObjectName("fact_button")
        self.fact_button.setToolTip("Click para ver otro dato")
        self.fact_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fact_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.fact_button.clicked.connect(self.siguiente_dato)
        layout.addWidget(self.fact_button, 1)  # stretch: se lleva el ancho sobrante

        return panel

    def actualizar_stats(self):
        """
        Recalcula barra y datos curiosos desde la base (db.obtener_estadisticas) y los muestra.
        Conserva el dato que se estaba viendo, salvo que la lista nueva sea más corta.
        """
        stats = self.db.obtener_estadisticas()
        self.progress_label.setText(barra_progreso(stats["completadas"], stats["total"]))
        self.datos_curiosos = armar_datos_curiosos(stats)
        self.indice_dato %= len(self.datos_curiosos)
        self.fact_button.setText(self.datos_curiosos[self.indice_dato])

    def siguiente_dato(self):
        """Slot del click en el dato curioso: pasa al siguiente (circular)."""
        self.indice_dato = (self.indice_dato + 1) % len(self.datos_curiosos)
        self.fact_button.setText(self.datos_curiosos[self.indice_dato])

    def _crear_estado_vacio(self, solo_completadas) -> QFrame:
        """
        Pantalla de "no hay nada para mostrar": un dibujo ASCII + un consejo, coherentes
        con la tipografía monoespaciada. El texto cambia si el vacío es por el filtro
        de completadas.
        """
        arte = "\n".join([
            "  +-------------+",
            "  |   ( o_o )   |",
            "  |   ~ zzz ~   |",
            "  +-------------+",
        ])
        if solo_completadas:
            titulo, tip = arte, "Todavía no completaste nada en esta lista.\nTildá una tarea para verla acá."
        else:
            titulo, tip = arte, "Nada por hacer.\nEscribí arriba y apretá Enter, o usá «+ Nueva Tarea»."

        marco = QFrame()
        marco.setObjectName("empty_state")
        layout = QVBoxLayout(marco)
        layout.setContentsMargins(0, 40, 0, 0)
        layout.setSpacing(14)

        dibujo = QLabel(titulo)
        dibujo.setObjectName("empty_art")
        dibujo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dibujo)

        consejo = QLabel(tip)
        consejo.setObjectName("empty_tip")
        consejo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(consejo)
        return marco

    def mostrar_menu_tarea(self, tarjeta, boton):
        """
        Menú contextual ⋮ de una tarjeta: Editar / Mover a lista / Eliminar.
        `tarjeta` aporta task_id, descripcion, completada y categoria_id; `boton` es el
        ⋮ (solo para posicionar el menú debajo con mapToGlobal). Necesita self.db para
        listar las categorías destino (se excluye la actual). QMenu.exec() es bloqueante
        y devuelve la QAction elegida (también las de submenús) o None si se cancela.
        """
        menu = QMenu(self)
        accion_editar = menu.addAction("✏️  Editar")

        submenu = menu.addMenu("📂  Mover a lista")
        destinos = {}  # QAction -> (categoria_id, nombre)
        for cid, nombre in self.db.obtener_categorias():
            if cid != tarjeta.categoria_id:
                destinos[submenu.addAction(nombre)] = (cid, nombre)
        submenu.setEnabled(bool(destinos))

        menu.addSeparator()
        accion_eliminar = menu.addAction("🗑️  Eliminar")

        elegida = menu.exec(boton.mapToGlobal(QPoint(0, boton.height())))
        if elegida is None:
            return
        if elegida == accion_editar:
            self.abrir_detalle_tarea_card(tarjeta.task_id, tarjeta.descripcion, tarjeta.completada)
        elif elegida == accion_eliminar:
            self.eliminar_tarea_ui(tarjeta.task_id)
        elif elegida in destinos:
            self.mover_tarea_ui(tarjeta.task_id, *destinos[elegida])

    def mover_tarea_ui(self, id_tarea, categoria_id, nombre_lista):
        """Mueve la tarea a otra lista (db.mover_tarea) y redibuja; si estás viendo una lista puntual, la tarjeta sale de la vista."""
        self.db.mover_tarea(id_tarea, categoria_id)
        self.statusBar().showMessage(f"Tarea #{id_tarea} movida a «{nombre_lista}».", 3000)
        self.recargar_lista()

    def eliminar_tarea_ui(self, id_tarea):
        """Elimina una tarea desde el menú ⋮, pidiendo confirmación (en el menú es fácil clickear sin querer)."""
        respuesta = QMessageBox.question(
            self, "Eliminar tarea", f"¿Eliminar la tarea #{id_tarea}? Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        self.db.eliminar_tarea(id_tarea)
        if self.detail_window is not None and self.detail_window.task_id == id_tarea:
            self.detail_window.close()
        self.recargar_lista()

    def preparar_entrada_animada(self, id_tarea):
        """Marca qué tarjeta debe aparecer con fade-in en el próximo redibujado (la usa TaskCard al tildarse)."""
        self._tarea_recien_movida = id_tarea

    def alternar_completadas(self):
        """Slot del separador: invierte el colapso y redibuja la grilla."""
        self.completadas_colapsadas = not self.completadas_colapsadas
        self.obtener_tareas()

    def toggle_completada_card(self, id_tarea, completada):
        """
        Slot del checkbox de una TaskCard: persiste el nuevo estado y redibuja la grilla
        (la tarjeta cambia de bloque: pendientes <-> completadas).
        `completada` es el estado NUEVO. Si el panel de detalle estaba abierto sobre
        esa misma tarea, se cierra: tendría el estado viejo y pisaría el cambio al guardar.
        """
        if completada:
            self.db.marcar_como_completada(id_tarea)
        else:
            self.db.desmarcar_como_completada(id_tarea)

        if self.detail_window is not None and self.detail_window.task_id == id_tarea:
            self.detail_window.close()

        self.recargar_lista()

    def abrir_detalle_tarea_card(self, id_tarea, descripcion, completada):
        """Abre el panel de detalle. Le pasamos el estado actual para que sepa si mostrar 'Marcar' o 'Desmarcar'."""
        if self.detail_window is not None:
            self.detail_window.close()

        self.detail_window = DetailWindow(
            task_id=id_tarea, 
            task_desc=descripcion, 
            completada=completada,
            db_connection=self.db, 
            refresh_callback=self.recargar_lista 
        )
        self.detail_window.show()


    def aplicar_sombra_dura(self, widget):
        """Genera una instancia única de sombra dura y se la aplica al widget recibido."""
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(0)
        sombra.setColor(QColor(0, 0, 0, 150))
        sombra.setOffset(4, 6)
        widget.setGraphicsEffect(sombra)

    def aplicar_sombra_suave(self, widget):
        """
        Sombra difusa (con blur) para elementos que necesitan sensación de 'elevación'
        sin el look brutalista de los botones — hoy la usan las TaskCard.
        Nota Qt: cada QGraphicsEffect solo puede estar asignado a un widget a la vez,
        por eso se crea una instancia nueva en cada llamada (mismo motivo que en aplicar_sombra_dura).
        """
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(28)
        sombra.setColor(QColor(0, 0, 0, 70))  # negro con alpha bajo -> sombra tenue, no un bloque sólido
        sombra.setOffset(4, 8)
        widget.setGraphicsEffect(sombra)


    def closeEvent(self, event):
        """
        Se llama cuando la ventana se cierra. Aquí cerramos la conexión a la base de datos.
        """
        self.db.cerrar_conexion()
        event.accept()  # Acepta el evento de cierre
        print("Conexión a la base de datos cerrada correctamente.")

    def recargar_lista(self):
        """Vuelve a poblar la grilla desde la base de datos (obtener_tareas ya limpia antes de dibujar)."""
        self.obtener_tareas()

    def limpiar_lista(self):
        """Elimina todos los widgets (tarjetas) de la grilla actual."""
        # Hay que recorrer la grilla al revés para ir borrando los elementos de forma segura
        for i in reversed(range(self.tasks_grid.count())): 
            widget = self.tasks_grid.itemAt(i).widget()
            if widget is not None: 
                widget.deleteLater() # Método de PyQt para destruir el widget gráficamente
