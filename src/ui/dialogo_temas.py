from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)
from ui.temas import TEMAS


class DialogoTemas(QDialog):
    """
    Diálogo modal de Configuración > Temas.
    Datos que necesita: `tema_actual` (clave de TEMAS, para marcar el radio correcto) y
    `al_cambiar` (callable que recibe la clave elegida; MainWindow lo usa para guardar
    el tema y redibujar la grilla). El cambio se aplica en vivo, sin botón "Aplicar".
    """

    def __init__(self, tema_actual, al_cambiar, parent=None):
        super().__init__(parent)
        self.al_cambiar = al_cambiar

        self.setObjectName("dialogo_temas")
        self.setWindowTitle("Configuración · Temas")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(6)

        titulo = QLabel("Tema de las tarjetas")
        titulo.setObjectName("dialogo_titulo")
        layout.addWidget(titulo)
        layout.addSpacing(8)

        # QButtonGroup hace los radios mutuamente excluyentes aunque no compartan layout
        self.grupo = QButtonGroup(self)
        for clave, info in TEMAS.items():
            radio = QRadioButton(info["nombre"])
            radio.setObjectName("tema_radio")
            radio.setChecked(clave == tema_actual)
            # c=clave "congela" el valor de esta vuelta del for (misma razón que en poblar_categorias)
            radio.toggled.connect(lambda marcado, c=clave: self._al_marcar(c, marcado))
            self.grupo.addButton(radio)
            layout.addWidget(radio)

            descripcion = QLabel(info["descripcion"])
            descripcion.setObjectName("tema_desc")
            descripcion.setWordWrap(True)
            layout.addWidget(descripcion)
            layout.addSpacing(6)

        layout.addStretch()

        cerrar = QPushButton("Listo")
        cerrar.setObjectName("dialogo_cerrar")
        cerrar.clicked.connect(self.accept)
        layout.addWidget(cerrar)

    def _al_marcar(self, clave, marcado):
        """`toggled` se emite también al DESmarcar el radio anterior; solo importa el que queda marcado."""
        if marcado:
            self.al_cambiar(clave)
