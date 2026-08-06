import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # database = Database() # Inicializa la base de datos al iniciar la aplicación
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec()) # app.exec es un loop que espera a que se cierre la ventana para terminar