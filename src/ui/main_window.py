from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPointF
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
    QGridLayout,
    QFrame,
    QScrollArea,
    QButtonGroup,
    QInputDialog,
    QMessageBox,
    QMenu,
)
from logic.database import Database


class TaskCard(QFrame):
    def __init__(self, task_id, descripcion, completada, main_window):
        super().__init__()
        self.task_id = task_id
        self.descripcion = descripcion
        self.completada = completada  # se guarda para poder pasarlo al abrir el detalle
        self.main_window = main_window
        
        self.setObjectName("task_card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Layout interno: descripción arriba (contenido principal), ID como
        # metadato chico abajo -> jerarquía visual en vez de todo del mismo peso
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        desc_label = QLabel(self.descripcion)
        desc_label.setObjectName("task_desc")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.setStyleSheet("background-color: #434e8f;") # azul oscuro para pendientes

        if completada:
            # si esta completada, aplicar el selector del qss
            desc_label.setProperty("completada", "true")

            desc_label.style().unpolish(desc_label)
            desc_label.style().polish(desc_label)
            self.setStyleSheet("background-color: #81a66f;") # verde para completadas

        layout.addWidget(desc_label)
        layout.addStretch()  # empuja el ID hacia el pie de la tarjeta, sin importar cuánto texto tenga la descripción

        id_label = QLabel(f"Tarea #{self.task_id}")
        id_label.setObjectName("task_id_label")
        id_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(id_label)

        self.setLayout(layout)
        
        self.main_window.aplicar_sombra_dura(self)
        self.setFixedSize(200, 160)


    def mousePressEvent(self, event):
        self.main_window.abrir_detalle_tarea_card(self.task_id, self.descripcion, self.completada)

    def enterEvent(self, event):
        """Se dispara cuando el cursor entra en la tarjeta (Hover in)"""
        efecto = self.graphicsEffect()
        # Verificar que tenga una sombra aplicada
        if isinstance(efecto, QGraphicsDropShadowEffect):
            # Crear la animación apuntando a la propiedad "offset" de la sombra
            self.anim_shadow = QPropertyAnimation(efecto, b"offset")
            self.anim_shadow.setDuration(150)
            self.anim_shadow.setStartValue(efecto.offset())
            # Estirar la sombra hacia abajo y a la derecha simulando que la tarjeta sube
            self.anim_shadow.setEndValue(QPointF(6.0, 12.0)) 
            self.anim_shadow.setEasingCurve(QEasingCurve.Type.OutQuad) # Curva de aceleración suave
            self.anim_shadow.start()
            
        super().enterEvent(event) # llamar al evento original

    def leaveEvent(self, event):
        """Se dispara cuando el cursor sale de la tarjeta (Hover out)"""
        efecto = self.graphicsEffect()
        if isinstance(efecto, QGraphicsDropShadowEffect):
            self.anim_shadow = QPropertyAnimation(efecto, b"offset")
            self.anim_shadow.setDuration(150)
            self.anim_shadow.setStartValue(efecto.offset())
            self.anim_shadow.setEndValue(QPointF(4.0, 6.0)) 
            self.anim_shadow.setEasingCurve(QEasingCurve.Type.OutQuad)
            self.anim_shadow.start()
            
        super().leaveEvent(event)    

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
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: transparent;") # Para que no pise el fondo general

        # Contenedor interno donde van a ir las tarjetas
        self.tasks_container = QWidget()
        self.scroll_area.setWidget(self.tasks_container)

        # La grilla que ordenará las tarjetas
        self.tasks_grid = QGridLayout(self.tasks_container)
        self.tasks_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        self.tasks_grid.setSpacing(16)  # espacio entre tarjetas

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

        self.filter_button = QPushButton("✅")
        self.filter_button.setObjectName("filter_button")
        self.filter_button.setCheckable(True)
        self.aplicar_sombra_dura(self.filter_button)
        layout.addWidget(self.filter_button)

        return header

    def seleccionar_seccion(self):
        """
        Handler común para todos los botones de navegación del sidebar.
        self.sender() devuelve el QPushButton concreto que disparó la señal 'clicked';
        así no hace falta un método distinto por cada botón.
        """
        boton = self.sender()
        if boton.text().strip() != "✅  Tareas":
            self.statusBar().showMessage(f"🚧 «{boton.text().strip()}» todavía no está implementado.", 4000)

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
            Dibuja la grilla separando primero las pendientes y luego las completadas.
            Fuerza un salto de línea en la grilla para crear una división visual.
            """
            self.limpiar_lista()  
            tareas = self.db.obtener_tareas(self.categoria_actual)

            solo_completadas = self.filter_button.isChecked()
            MAX_COLUMNAS = 3
            tarjetas_mostradas = 0  

            # 1. Separar las tareas en dos listas lógicas
            if (solo_completadas):
                pendientes = []
            else:
                pendientes = [t for t in tareas if not t[2]]

            completadas = [t for t in tareas if t[2]]

            # 2. Dibujar tareas Pendientes primero
            for id_tarea, descripcion, completada in pendientes:
                tarjeta = TaskCard(id_tarea, descripcion, completada, self)
                fila = tarjetas_mostradas // MAX_COLUMNAS
                columna = tarjetas_mostradas % MAX_COLUMNAS
                self.tasks_grid.addWidget(tarjeta, fila, columna)
                tarjetas_mostradas += 1

            # 3. Generar un salto visual antes de las completadas (si hay de ambas)
            if completadas and pendientes:
                # Si la fila actual de pendientes no está llena, adelantamos el contador 
                # para forzar que la siguiente tarjeta arranque en la columna 0 de una fila nueva.
                resto = tarjetas_mostradas % MAX_COLUMNAS
                if resto != 0:
                    tarjetas_mostradas += (MAX_COLUMNAS - resto)

            # 4. Dibujar tareas Completadas al final
            for id_tarea, descripcion, completada in completadas:
                tarjeta = TaskCard(id_tarea, descripcion, completada, self)
                fila = tarjetas_mostradas // MAX_COLUMNAS
                columna = tarjetas_mostradas % MAX_COLUMNAS
                self.tasks_grid.addWidget(tarjeta, fila, columna)
                tarjetas_mostradas += 1

    
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
