import os
from PyQt6.QtGui import QAction, QIcon, QColor
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QLabel,
    QMainWindow,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QPushButton,
    QListWidget,
    QHBoxLayout,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QFrame,
    QScrollArea
)
from logic.database import Database
from PyQt6 import uic

class TaskCard(QFrame):
    def __init__(self, task_id, descripcion, completada, main_window):
        super().__init__()
        self.task_id = task_id
        self.descripcion = descripcion
        self.main_window = main_window
        
        self.setObjectName("task_card")
        
        # "#" para que el estilo SOLO aplique a la tarjeta padre y no a los textos
        self.setStyleSheet("""
            #task_card {
                background-color: #434e8f;
                border: 2px solid black; /*#2c3e50;*/
                border-radius: 12px;
            }
        """)
        
        # Layout interno de la tarjeta
        layout = QVBoxLayout()
        
        # Etiqueta del ID
        id_label = QLabel(f" -- Tarea #{self.task_id} -- ")
        id_label.setStyleSheet("color: white; font-weight: bold;") 
        
        # Etiqueta de la descripción
        desc_label = QLabel(self.descripcion)
        desc_label.setWordWrap(True)

        if completada:
            fuente = desc_label.font()
            fuente.setStrikeOut(True)
            desc_label.setFont(fuente)
            desc_label.setStyleSheet("color: #c8cce6;")
            
        layout.addWidget(id_label)
        layout.addWidget(desc_label)
        self.setLayout(layout)
        
        self.main_window.aplicar_sombra_dura(self)
        self.setFixedSize(180, 150)

    def mousePressEvent(self, event):
        self.main_window.abrir_detalle_tarea_card(self.task_id, self.descripcion)

class DetailWindow(QWidget):
    def __init__(self, task_id, task_desc, db_connection, refresh_callback):
        super().__init__()
        self.task_id = task_id
        self.db = db_connection
        self.refresh_callback = refresh_callback # Función para recargar la lista principal

        self.setWindowTitle(f"Detalle de Tarea #{self.task_id}")
        self.resize(300, 200)

        # Layout principal
        layout = QVBoxLayout()

        # 1. Input para modificar el texto
        layout.addWidget(QLabel("Descripción de la tarea:"))
        self.desc_input = QLineEdit(task_desc)
        layout.addWidget(self.desc_input)

        # 2. Botón para Guardar Cambios
        self.save_button = QPushButton("Guardar Cambios")
        self.save_button.setStyleSheet("background-color: #FFC107; color: black; font-weight: bold;")
        
        # 3. Botón para Marcar Completada
        self.complete_button = QPushButton("Marcar como Completada")
        self.complete_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        # 4. Botón para Eliminar
        self.delete_button = QPushButton("Eliminar Tarea")
        self.delete_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

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
        self.resize(600, 800) # Ancho, Alto inicial
        self.db = Database() # Inicializa la base de datos al iniciar la aplicación
        self.detail_window = None  # Ventana de detalle de tarea

        ## -- Forma de cargar el UI desde un archivo .ui (opcional) generado por Qt Designer --
        # # os.path para que no importe desde dónde ejecuta el main.py
        # ui_path = os.path.join(os.path.dirname(__file__), "main_window.ui")
        # uic.loadUi(ui_path, self)        


        # 1. Widget central (Obligatorio en QMainWindow)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 2. Layout principal (Caja Vertical)
        main_layout = QVBoxLayout(self.central_widget)

        # 3. Layout superior (Caja Horizontal para el input y el botón)
        # input_layout = QHBoxLayout()

        # 4. Layout inferior 
        bottom_layout = QHBoxLayout()

        # 5. Layout de la grilla para organizar los botones y el input
        grid_layout = QGridLayout()


        # --- Componentes ---
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("¿Qué tenés que hacer hoy?")
        
        self.add_button = QPushButton("Agregar Tarea")
        self.add_button.setObjectName("add_button")
        # self.add_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.aplicar_sombra_dura(self.add_button)

        self.tasks_button = QPushButton("Ver tareas")
        self.tasks_button.setObjectName("tasks_button")
        self.aplicar_sombra_dura(self.tasks_button)
        # self.tasks_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;") 

        self.clear_button = QPushButton("Limpiar lista")
        self.clear_button.setObjectName("clear_button")
        self.aplicar_sombra_dura(self.clear_button)
        # self.clear_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

        bottom_layout.addWidget(self.clear_button)

        # Fila 0, Columna 0: Botón "Ver tareas"
        grid_layout.addWidget(self.tasks_button, 0, 0)

        # Fila 0, Columna 1: El Input. 
        grid_layout.addWidget(self.task_input, 0, 1, 2, 4)

        # Fila 0, Columna 5: Botón "Agregar Tarea"
        grid_layout.addWidget(self.add_button, 0, 5)
        # Agregar la grilla al layout principal
        main_layout.addLayout(grid_layout)



        # Barra de herramientas (Toolbar)
        # Utilidades: Filtrar tareas completadas, por fecha, etc. (Por ahora solo filtrado)
        toolbar = QToolBar("Barra de Herramientas")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)

        filter_action = QAction(QIcon("images/icons/tick-circle.png"), "&Tareas completadas", self)
        filter_action.setStatusTip("Filtrar por tareas completadas")
        filter_action.triggered.connect(self.filtrar_tareas_completadas)
        filter_action.setCheckable(True)
        toolbar.addAction(filter_action) 

        self.setStatusBar(QStatusBar(self))    
        
        # input_layout.addWidget(self.tasks_button)
        # input_layout.addWidget(self.task_input)
        # input_layout.addWidget(self.add_button)

        # Lista de tareas (El componente principal)
        # self.task_list = QListWidget()
        # Área de scroll y matriz de tareas (Reemplaza a QListWidget)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: transparent;") # Para que no pise el fondo general
        
        # Contenedor interno donde van a ir las tarjetas
        self.tasks_container = QWidget()
        self.scroll_area.setWidget(self.tasks_container)
        
        # La grilla que ordenará las tarjetas
        self.tasks_grid = QGridLayout(self.tasks_container)
        self.tasks_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Ensamblar todo en la caja vertical principal
        main_layout.addWidget(self.scroll_area) # Agregar el scroll en vez de la lista
        # main_layout.addLayout(input_layout)
        # main_layout.addWidget(self.task_list)
        main_layout.addLayout(bottom_layout)


        # Conectar Señales a Slots (Funciones)
        self.add_button.clicked.connect(self.agregar_tarea_ui)
        self.tasks_button.clicked.connect(self.obtener_tareas)
        # Esto permite agregar la tarea apretando "Enter" además del clic
        # self.task_input.returnPressed.connect(self.agregar_tarea_ui) 
        # self.task_list.itemClicked.connect(self.abrir_detalle_tarea)
        self.clear_button.clicked.connect(self.limpiar_lista)


    def agregar_tarea_ui(self):
        """
        Toma el texto del input, lo guarda en la base de datos y recarga la matriz visual.
        """
        texto = self.task_input.text().strip() 

        if texto: # Solo agrega si no está vacío
            # Llamar a la función de la base de datos para guardar la tarea
            id = self.db.agregar_tarea(texto)

            if id is not None:  # Verifica que se haya guardado correctamente
                # En lugar de intentar agregar un ítem suelto, redibuja toda la matriz
                self.recargar_lista() 
                
                self.task_input.clear() # Limpia el input para la siguiente tarea
            else:
                self.statusBar().showMessage("!⚠ Error al agregar la tarea a la base de datos.", 5000)

    # def agregar_tarea_ui(self):
    #     """
    #     Toma el texto del input, lo guarda en la base de datos y lo muestra en la lista.
    #     """
    #     texto = self.task_input.text().strip() # .strip() saca los espacios en blanco extra

    #     if texto: # Solo agrega si no está vacío
    #         # llamar a la función de la base de datos para guardar la tarea
    #         id = self.db.agregar_tarea(texto)

    #         if id is not None:  # Verifica que se haya guardado correctamente

    #             self.task_list.addItem(f"{id}. {texto}") # Muestra el ID junto con la descripción
    #             self.task_input.clear() # Limpia el input para la siguiente tarea
    #         else:
    #             self.statusBar().showMessage("!⚠ Error al agregar la tarea a la base de datos.", 5000) # Mensaje por 5 segundos
    
    # def completar_tarea_ui(self, item):
    #     """
    #     Marca la tarea como completada al hacer doble clic. 
    #     """
    #     font = item.font()
    #     font.setStrikeOut(not font.strikeOut()) # Alterna el tachado
    #     item.setFont(font)

    #     # actualizar la base de datos para marcar la tarea como completada:
    #     # extraer el ID de la tarea del texto del item y luego actualizar la base de datos
    #     id = int(item.text().split('. ')[0])  # Extrae el ID del texto del item
    #     self.db.marcar_como_completada(id)  # Llamar a un método que actualice


    def obtener_tareas(self):

        """Obtiene las tareas y las dibuja como tarjetas en la grilla."""
        tareas = self.db.obtener_tareas()
        
        # Cuántas columnas como máximo
        MAX_COLUMNAS = 3
        
        for index, tarea in enumerate(tareas):
            id_tarea, descripcion, completada = tarea
            
            # Nueva tarjeta
            tarjeta = TaskCard(id_tarea, descripcion, completada, self)
            
            # Saber en que fila y columna poner la tarjeta según el índice:
            fila = index // MAX_COLUMNAS
            columna = index % MAX_COLUMNAS
            
            # Agregar el widget en su celda correspondiente
            self.tasks_grid.addWidget(tarjeta, fila, columna)

        # tareas = self.db.obtener_tareas()
        # for tarea in tareas:
        #     id, descripcion, completada = tarea
        #     item_text = f"{id}. {descripcion}"
        #     if completada:
        #         item_text += " (Completada)"
        #     self.task_list.addItem(item_text)
    
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

    # def abrir_detalle_tarea(self, item):
    #     """Abre el panel de control de la tarea seleccionada."""
    #     texto_completo = item.text()
        
    #     # Separar el ID de la descripción usando el punto
    #     try:
    #         id_str, descripcion = texto_completo.split('. ', 1)
    #         id_tarea = int(id_str)
            
    #         # Limpiar la etiqueta " (Completada)" si la tiene, para no editarla junto con el texto
    #         if descripcion.endswith(" (Completada)"):
    #             descripcion = descripcion.replace(" (Completada)", "")
    #     except ValueError:
    #         print("Error al parsear el ID de la tarea seleccionada.")
    #         return

    #     # Gestionar la ventana hija
    #     if self.detail_window is not None:
    #         self.detail_window.close()

    #     # Instanciar la nueva ventana pasándole los datos, la DB y la función para recargar
    #     self.detail_window = DetailWindow(
    #         task_id=id_tarea, 
    #         task_desc=descripcion, 
    #         db_connection=self.db, 
    #         refresh_callback=self.recargar_lista # Usamos un nuevo método para recargar
    #     )
    #     self.detail_window.show()

    def filtrar_tareas_completadas(self, checked):
        """
        Filtra la matriz de tareas para mostrar solo las completadas o todas.
        """
        self.limpiar_lista()
        tareas = self.db.obtener_tareas()
        
        MAX_COLUMNAS = 3
        tarjetas_mostradas = 0 # contador nuevo para la grilla filtrada
        
        for tarea in tareas:
            id_tarea, descripcion, completada = tarea
            
            # Si el filtro está activo y la tarea NO está completada, la saltamos
            if checked and not completada:
                continue  
            
            # Nueva tarjeta
            tarjeta = TaskCard(id_tarea, descripcion, completada, self)
            
            fila = tarjetas_mostradas // MAX_COLUMNAS
            columna = tarjetas_mostradas % MAX_COLUMNAS
            
            self.tasks_grid.addWidget(tarjeta, fila, columna)
            tarjetas_mostradas += 1


    # def filtrar_tareas_completadas(self, checked):
    #     """
    #     Filtra la lista de tareas para mostrar solo las completadas o todas según el estado del checkbox.
    #     """
    #     self.task_list.clear()  # Limpiar la lista antes de repoblarla
    #     tareas = self.db.obtener_tareas()
        
    #     for tarea in tareas:
    #         id, descripcion, completada = tarea
    #         if checked and not completada:
    #             continue  # Si está marcado y la tarea no está completada, saltarla
    #         item_text = f"{id}. {descripcion}"
    #         if completada:
    #             item_text += " (Completada)"
    #         self.task_list.addItem(item_text)

    def aplicar_sombra_dura(self, widget):
        """Genera una instancia única de sombra dura y se la aplica al widget recibido."""
        sombra = QGraphicsDropShadowEffect()
        sombra.setBlurRadius(0)
        sombra.setColor(QColor(0, 0, 0))
        sombra.setOffset(4, 4)
        widget.setGraphicsEffect(sombra)


    def closeEvent(self, event):
        """
        Se llama cuando la ventana se cierra. Aquí cerramos la conexión a la base de datos.
        """
        self.db.cerrar_conexion()
        event.accept()  # Acepta el evento de cierre
        print("Conexión a la base de datos cerrada correctamente.")

    def recargar_lista(self):
        """Limpia la lista actual y la vuelve a poblar desde la base de datos."""
        self.limpiar_lista()
        self.obtener_tareas()

    def limpiar_lista(self):
        """Elimina todos los widgets (tarjetas) de la grilla actual."""
        # Hay que recorrer la grilla al revés para ir borrando los elementos de forma segura
        for i in reversed(range(self.tasks_grid.count())): 
            widget = self.tasks_grid.itemAt(i).widget()
            if widget is not None: 
                widget.deleteLater() # Método de PyQt para destruir el widget gráficamente
