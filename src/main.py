import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.temas import generar_qss_temas

if __name__ == "__main__":
    app = QApplication(sys.argv)

# 1. Definir la ruta absoluta al archivo QSS
    # Esto evita problemas sin importar desde dónde ejecutes el script
    qss_path = os.path.join(os.path.dirname(__file__), "ui", "estilos.qss")
    
    # 2. Leer el archivo y aplicar los estilos globalmente
    try:
        with open(qss_path, "r", encoding="utf-8") as estilo_file:
            # Base + temas alternativos (Color por lista / Pastel), generados desde ui/temas.py
            app.setStyleSheet(estilo_file.read() + generar_qss_temas())
    except FileNotFoundError:
        print("Aviso: No se encontró el archivo estilos.qss. Iniciando sin estilos personalizados.")

    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec()) # app.exec es un loop que espera a que se cierre la ventana para terminar