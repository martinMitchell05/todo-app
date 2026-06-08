import sys
from ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
# Modulos principales de PyQt6 ---> QtWidgets, QtCore, QtGui


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) # app.exec es un loop que espera a que se cierre la ventana para terminar