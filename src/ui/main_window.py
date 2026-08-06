# from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence
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
)
from logic.database import Database

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
        self.setWindowTitle("Mi To-Do App")
        self.resize(600, 700) # Ancho, Alto inicial
        self.db = Database() # Inicializa la base de datos al iniciar la aplicación
        self.detail_window = None  # Ventana de detalle de tarea


        # 1. Widget central (Obligatorio en QMainWindow)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # 2. Layout principal (Caja Vertical)
        main_layout = QVBoxLayout(self.central_widget)

        # 3. Layout superior (Caja Horizontal para el input y el botón)
        input_layout = QHBoxLayout()

        # 4. Layout inferior 
        bottom_layout = QHBoxLayout()

        # --- Componentes ---
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("¿Qué tenés que hacer hoy?")
        
        self.add_button = QPushButton("Agregar Tarea")
        self.add_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        self.tasks_button = QPushButton("Ver tareas")
        self.tasks_button.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;") 

        self.clear_button = QPushButton("Limpiar lista")
        self.clear_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        
        # Agregamos el input y el botón a su caja horizontal
        input_layout.addWidget(self.tasks_button)
        input_layout.addWidget(self.task_input)
        input_layout.addWidget(self.add_button)

        # 4. Lista de tareas (El componente principal)
        self.task_list = QListWidget()

        # 5. Ensamblar todo en la caja vertical principal
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.task_list)

        main_layout.addLayout(bottom_layout)
        bottom_layout.addWidget(self.clear_button)

        # 6. Conectar Señales a Slots (Interactividad)
        self.add_button.clicked.connect(self.agregar_tarea_ui)
        self.tasks_button.clicked.connect(self.obtener_tareas)
        # Esto permite agregar la tarea apretando "Enter" además del clic
        self.task_input.returnPressed.connect(self.agregar_tarea_ui) 
        self.task_list.itemClicked.connect(self.abrir_detalle_tarea)
        self.clear_button.clicked.connect(self.limpiar_lista)

    def agregar_tarea_ui(self):
        """
        Toma el texto del input, lo guarda en la base de datos y lo muestra en la lista.
        """
        texto = self.task_input.text().strip() # .strip() saca los espacios en blanco extra

        # llamar a la función de la base de datos para guardar la tarea
        id = self.db.agregar_tarea(texto)
        
        # verificar que la base de datos guarde la tarea correctamente antes de agregarla a la lista

        # mostrar la tarea en la lista solo si se guardó correctamente en la base de datos
        if texto: # Solo agrega si no está vacío
            self.task_list.addItem(f"{id}. {texto}") # Muestra el ID junto con la descripción
            self.task_input.clear() # Limpia el input para la siguiente tarea
    
    def completar_tarea_ui(self, item):
        """
        Marca la tarea como completada al hacer doble clic. 
        """
        font = item.font()
        font.setStrikeOut(not font.strikeOut()) # Alterna el tachado
        item.setFont(font)

        # actualizar la base de datos para marcar la tarea como completada:
        # extraer el ID de la tarea del texto del item y luego actualizar la base de datos
        id = int(item.text().split('. ')[0])  # Extrae el ID del texto del item
        self.db.marcar_como_completada(id)  # Llamar a un método que actualice


    def obtener_tareas(self):
        """
        Obtiene todas las tareas de la base de datos y las muestra en la lista.
        """
        tareas = self.db.obtener_tareas()
        for tarea in tareas:
            id, descripcion, completada = tarea
            item_text = f"{id}. {descripcion}"
            if completada:
                item_text += " (Completada)"
            self.task_list.addItem(item_text)

    def abrir_detalle_tarea(self, item):
        """Abre el panel de control de la tarea seleccionada."""
        texto_completo = item.text()
        
        # Separar el ID de la descripción usando el punto
        try:
            id_str, descripcion = texto_completo.split('. ', 1)
            id_tarea = int(id_str)
            
            # Limpiar la etiqueta " (Completada)" si la tiene, para no editarla junto con el texto
            if descripcion.endswith(" (Completada)"):
                descripcion = descripcion.replace(" (Completada)", "")
        except ValueError:
            print("Error al parsear el ID de la tarea seleccionada.")
            return

        # Gestionar la ventana hija
        if self.detail_window is not None:
            self.detail_window.close()

        # Instanciar la nueva ventana pasándole los datos, la DB y la función para recargar
        self.detail_window = DetailWindow(
            task_id=id_tarea, 
            task_desc=descripcion, 
            db_connection=self.db, 
            refresh_callback=self.recargar_lista # Usamos un nuevo método para recargar
        )
        self.detail_window.show()


    def closeEvent(self, event):
        """
        Se llama cuando la ventana se cierra. Aquí cerramos la conexión a la base de datos.
        """
        self.db.cerrar_conexion()
        event.accept()  # Acepta el evento de cierre
        print("Conexión a la base de datos cerrada correctamente.")

    def recargar_lista(self):
        """Limpia la lista actual y la vuelve a poblar desde la base de datos."""
        self.task_list.clear()
        self.obtener_tareas()

    def limpiar_lista(self):
        """
        Limpia la lista de tareas en la interfaz. 
        Nota: Esto no elimina las tareas de la base de datos.
        """
        self.task_list.clear()