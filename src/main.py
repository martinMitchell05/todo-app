import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton
# Modulos principales de PyQt6 ---> QtWidgets, QtCore, QtGui


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__() # cuando se crea una subclase de Qt siempre se debe inicializar el super() para que Qt construya el objeto correctamente
        
        self.setWindowTitle("Mi To-Do App")
        self.setGeometry(860, 240, 480, 640) # x, y, ancho, alto
        
        # Un texto de prueba en el medio
        label = QLabel("Entorno listo.", self)
        label.move(int(self.width()/2), int(self.height()/2))

        # Ejemplo de como crear un botón
        # button = QPushButton("Submit")
        # self.setCentralWidget(button) --> establece al boton en toda la ventana



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) # app.exec es un loop que espera a que se cierre la ventana para terminar