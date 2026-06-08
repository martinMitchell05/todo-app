from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget)
from PyQt6.QtCore import Qt
from logic.database import Database

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración básica de la ventana
        self.setWindowTitle("Mi To-Do App")
        self.resize(500, 600) # Ancho, Alto inicial

        # 1. Widget central (Obligatorio en QMainWindow)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 2. Layout principal (Caja Vertical)
        main_layout = QVBoxLayout(central_widget)

        # 3. Layout superior (Caja Horizontal para el input y el botón)
        input_layout = QHBoxLayout()
        
        # --- Componentes ---
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("¿Qué tenés que hacer hoy?")
        
        self.add_button = QPushButton("Agregar Tarea")
        
        # Agregamos el input y el botón a su caja horizontal
        input_layout.addWidget(self.task_input)
        input_layout.addWidget(self.add_button)

        # 4. Lista de tareas (El componente principal)
        self.task_list = QListWidget()

        # 5. Ensamblar todo en la caja vertical principal
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.task_list)

        # 6. Conectar Señales a Slots (Interactividad)
        self.add_button.clicked.connect(self.agregar_tarea_ui)
        # Esto permite agregar la tarea apretando "Enter" además del clic
        self.task_input.returnPressed.connect(self.agregar_tarea_ui) 

    def agregar_tarea_ui(self):
        """
        Captura el texto del input y lo muestra en la lista.
        Por ahora es solo visual, luego lo conectaremos con src/logic/
        """
        texto = self.task_input.text().strip() # .strip() saca los espacios en blanco extra
        
        if texto: # Solo agrega si no está vacío
            self.task_list.addItem(texto)
            self.task_input.clear() # Limpia el input para la siguiente tarea