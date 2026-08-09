from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
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
)
from logic.database import Database

class TaskCard(QFrame):
    def __init__(self, task_id, descripcion, completada, main_window):
        super().__init__()
        self.task_id = task_id
        self.descripcion = descripcion
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

        if completada:
            fuente = desc_label.font()
            fuente.setStrikeOut(True)
            desc_label.setFont(fuente)
            desc_label.setStyleSheet("color: #9aa0c9;")  # sobrescribe solo el color; el resto lo hereda del QSS

        layout.addWidget(desc_label)
        layout.addStretch()  # empuja el ID hacia el pie de la tarjeta, sin importar cuánto texto tenga la descripción

        id_label = QLabel(f"Tarea #{self.task_id}")
        id_label.setObjectName("task_id_label")
        id_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(id_label)

        self.setLayout(layout)
        
        self.main_window.aplicar_sombra_suave(self)
        self.setFixedSize(200, 160)
        self.setStyleSheet("background-color: #434e8f;")

    def mousePressEvent(self, event):
        self.main_window.abrir_detalle_tarea_card(self.task_id, self.descripcion)

class DetailWindow(QWidget):
    def __init__(self, task_id, task_desc, db_connection, refresh_callback):
        super().__init__()
        self.task_id = task_id
        self.db = db_connection
        self.refresh_callback = refresh_callback # Función para recargar la lista principal

        self.setWindowTitle(f"Detalle de Tarea #{self.task_id}")
        self.resize(400, 400)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Layout principal
        layout = QVBoxLayout()

        # 1. Input para modificar el texto
        self.label_desc = QLabel(f"Editar Tarea #{self.task_id}\n --- Descripción: ")
        self.label_desc.setObjectName("label_desc")

        layout.addWidget(self.label_desc)
        self.desc_input = QLineEdit(task_desc)
        self.desc_input.setObjectName("desc_input")
        layout.addWidget(self.desc_input)

        # 2. Botón para Guardar Cambios
        self.save_button = QPushButton("Guardar Cambios")
        self.save_button.setObjectName("save_button")
        #self.save_button.setStyleSheet("background-color: #FFC107; color: black; font-weight: bold;")
        
        # 3. Botón para Marcar Completada
        self.complete_button = QPushButton("Marcar como Completada")
        self.complete_button.setObjectName("complete_button")
        # self.complete_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        # 4. Botón para Eliminar
        self.delete_button = QPushButton("Eliminar Tarea")
        self.delete_button.setObjectName("delete_button")
        # self.delete_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

        # Agregamos los botones al layout
        layout.addWidget(self.save_button)
        layout.addWidget(self.complete_button)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

        # Conectamos los botones a sus funciones
        self.save_button.clicked.connect(self.guardar_cambios)
        self.complete_button.clicked.connect(self.completar_tarea)
        self.delete_button.clicked.connect(self.eliminar_tarea)

    def guardar_cambios(self):
        nueva_desc = self.desc_input.text().strip()
        if nueva_desc:
            self.db.actualizar_descripcion(self.task_id, nueva_desc)
            self.refresh_callback() # Le avisa a la ventana principal que actualice la lista
            self.close() # Cierra la ventana de detalle

    def completar_tarea(self):
        self.db.marcar_como_completada(self.task_id)
        self.refresh_callback()
        self.close()

    def eliminar_tarea(self):
        self.db.eliminar_tarea(self.task_id)
        self.refresh_callback()
        self.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración básica de la ventana
        self.setWindowTitle(" --- To-Do App / Personal --- ")
        self.resize(1000, 700) # Ancho, Alto inicial
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

        # ---------- SIDEBAR (navegación) ----------
        sidebar = self.crear_sidebar()
        root_layout.addWidget(sidebar)

        # ---------- CONTENIDO (header + alta rápida + tarjetas) ----------
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 16, 24, 16)
        root_layout.addWidget(content_widget, 1)  # stretch=1: se lleva todo el ancho restante

        header = self.crear_header()
        content_layout.addWidget(header)

        # --- Barra de alta rápida: input + acciones sobre las tareas ---
        grid_layout = QGridLayout()

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("¿Qué tenés que hacer hoy?")
        self.task_input.setObjectName("task_input")

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
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 24, 0, 24)
        layout.setSpacing(4)

        logo = QLabel("✅  ToDo App")
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

        # ---------- LISTAS (categorías reales, cargadas desde la base) ----------
        layout.addSpacing(12)

        listas_header = QLabel("LISTAS")
        listas_header.setObjectName("sidebar_section_label")
        layout.addWidget(listas_header)

        # Contenedor vacío: poblar_categorias() lo llena (y lo vuelve a llenar
        # cada vez que se crea una lista nueva)
        self.categorias_layout = QVBoxLayout()
        self.categorias_layout.setSpacing(4)
        layout.addLayout(self.categorias_layout)
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

        # "Todas las tareas" no es una fila de `categorias` — es la vista sin filtro
        boton_todas = QPushButton("🗂️  Todas las tareas")
        boton_todas.setObjectName("nav_button")
        boton_todas.setCheckable(True)
        boton_todas.setChecked(self.categoria_actual is None)
        boton_todas.clicked.connect(lambda: self.seleccionar_categoria(None, "Todas las tareas"))
        self.categoria_group.addButton(boton_todas)
        self.categorias_layout.addWidget(boton_todas)

        for categoria_id, nombre in self.db.obtener_categorias():
            boton = QPushButton(f"📋  {nombre}")
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
        Dibuja la grilla de tarjetas aplicando los dos filtros activos a la vez:
        la lista elegida en el sidebar (self.categoria_actual, None = todas) y el
        toggle "Ver solo completadas" del header (self.filter_button). Reemplaza a
        la vieja filtrar_tareas_completadas(), que duplicaba este mismo bucle.
        """
        self.limpiar_lista()  # evita duplicar tarjetas si se llama más de una vez
        tareas = self.db.obtener_tareas(self.categoria_actual)

        solo_completadas = self.filter_button.isChecked()
        MAX_COLUMNAS = 3
        tarjetas_mostradas = 0  # cuenta solo las que pasan el filtro, no el índice del for

        for id_tarea, descripcion, completada in tareas:
            if solo_completadas and not completada:
                continue

            tarjeta = TaskCard(id_tarea, descripcion, completada, self)

            fila = tarjetas_mostradas // MAX_COLUMNAS
            columna = tarjetas_mostradas % MAX_COLUMNAS
            self.tasks_grid.addWidget(tarjeta, fila, columna)
            tarjetas_mostradas += 1
    
    def abrir_detalle_tarea_card(self, id_tarea, descripcion):
        """Abre el panel de control. Ahora recibe los datos directos en lugar de parsear un string."""
        if self.detail_window is not None:
            self.detail_window.close()

        self.detail_window = DetailWindow(
            task_id=id_tarea, 
            task_desc=descripcion, 
            db_connection=self.db, 
            refresh_callback=self.recargar_lista 
        )
        self.detail_window.show()


    def aplicar_sombra_dura(self, widget):
        """Genera una instancia única de sombra dura y se la aplica al widget recibido."""
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(0)
        sombra.setColor(QColor(0, 0, 0, 150))
        sombra.setOffset(3, 5)
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
        sombra.setOffset(2, 6)
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
