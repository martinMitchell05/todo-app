import sqlite3
import os

class Database:
    def __init__(self, db_path=None):
        """Inicializa la conexión y asegura que la carpeta exista."""
        if db_path is None:
            # Ancla la ruta a la raíz del proyecto (un nivel arriba de logic/),
            # sin importar desde qué carpeta se ejecute python main.py.
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "tareas.db")

        # Se asegura de crear la carpeta "data" si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Conecta a la base de datos (si el archivo no existe, lo crea)
        self.conn = sqlite3.connect(db_path)
        self.crear_tabla()

    def crear_tabla(self):
        """Crea las tablas si es la primera vez, y migra bases viejas que no tenían categorías."""
        cursor = self.conn.cursor()

        # Tabla de categorías / listas (al estilo "Listas" de Microsoft To-Do)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion TEXT NOT NULL,
                completada BOOLEAN NOT NULL CHECK (completada IN (0, 1)) DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

        # --- Migración: si la base ya existía de antes de esta feature, "tareas"
        # no tiene la columna categoria_id todavía. PRAGMA table_info la chequea
        # sin tirar error (a diferencia de intentar el ALTER TABLE directo dos veces).
        cursor.execute("PRAGMA table_info(tareas)")
        columnas_existentes = [fila[1] for fila in cursor.fetchall()]
        if "categoria_id" not in columnas_existentes:
            cursor.execute("ALTER TABLE tareas ADD COLUMN categoria_id INTEGER REFERENCES categorias(id)")
            self.conn.commit()

        # Categoría por defecto ("Tareas"): existe siempre, y es donde caen las
        # tareas viejas que quedaron con categoria_id NULL tras la migración de arriba.
        cursor.execute("SELECT id FROM categorias WHERE nombre = ?", ("Tareas",))
        fila = cursor.fetchone()
        if fila:
            self.categoria_default_id = fila[0]
        else:
            cursor.execute("INSERT INTO categorias (nombre) VALUES (?)", ("Tareas",))
            self.conn.commit()
            self.categoria_default_id = cursor.lastrowid

        cursor.execute("UPDATE tareas SET categoria_id = ? WHERE categoria_id IS NULL", (self.categoria_default_id,))
        self.conn.commit()

    def crear_categoria(self, nombre: str) -> int:
        """Crea una lista/categoría nueva. Si ya existe una con ese nombre, devuelve su ID en vez de duplicarla."""
        cursor = self.conn.cursor()
        try:
            cursor.execute('INSERT INTO categorias (nombre) VALUES (?)', (nombre,))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Salta si "nombre" ya existe (columna UNIQUE) -> devolvemos la existente
            cursor.execute('SELECT id FROM categorias WHERE nombre = ?', (nombre,))
            return cursor.fetchone()[0]

    def obtener_categorias(self) -> list:
        """Trae todas las listas/categorías, en el orden en que se crearon."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, nombre FROM categorias ORDER BY fecha_creacion ASC')
        return cursor.fetchall()

    def eliminar_categoria(self, categoria_id: int):
        """
        Elimina una lista/categoría Y todas las tareas asociadas a ella (borrado en cascada).
        No se puede eliminar la categoría por defecto ("Tareas"): siempre tiene que
        quedar al menos una lista donde caigan las tareas sin categorizar (ver agregar_tarea).
        """
        if categoria_id == self.categoria_default_id:
            raise ValueError('No se puede eliminar la categoría por defecto ("Tareas").')

        cursor = self.conn.cursor()
        # SQLite no tiene ON DELETE CASCADE activado en esta tabla, así que el
        # cascadeo lo hacemos a mano: primero las tareas, después la categoría.
        # Ambos DELETE quedan en la misma transacción hasta el commit() del final,
        # así que si algo falla en el medio, no queda la base a medio borrar.
        cursor.execute('DELETE FROM tareas WHERE categoria_id = ?', (categoria_id,))
        cursor.execute('DELETE FROM categorias WHERE id = ?', (categoria_id,))
        self.conn.commit()

    def agregar_tarea(self, descripcion: str, categoria_id: int = None) -> int:
        """Inserta una nueva tarea en la categoría indicada (o en 'Tareas' si no se especifica) y devuelve su ID."""
        if categoria_id is None:
            categoria_id = self.categoria_default_id
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO tareas (descripcion, categoria_id) VALUES (?, ?)', (descripcion, categoria_id))
        self.conn.commit()
        return cursor.lastrowid # Te devuelve el ID por si lo necesitás en la interfaz

    def obtener_tareas(self, categoria_id: int = None) -> list:
        """
        Trae tareas. Si categoria_id es None, trae TODAS (vista "Todas las tareas");
        si se pasa un id puntual, filtra solo las de esa lista.
        """
        cursor = self.conn.cursor()
        if categoria_id is None:
            cursor.execute('SELECT id, descripcion, completada FROM tareas ORDER BY fecha_creacion ASC')
        else:
            cursor.execute(
                'SELECT id, descripcion, completada FROM tareas WHERE categoria_id = ? ORDER BY fecha_creacion ASC',
                (categoria_id,)
            )
        return cursor.fetchall()

    def marcar_como_completada(self, tarea_id: int):
        """Marca una tarea como completada."""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE tareas SET completada = 1 WHERE id = ?', (tarea_id,))
        self.conn.commit()

    def desmarcar_como_completada(self, tarea_id: int):
        """Vuelve una tarea a estado pendiente."""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE tareas SET completada = 0 WHERE id = ?', (tarea_id,))
        self.conn.commit()

    def eliminar_tarea(self, tarea_id: int):
        """Elimina una tarea específica por su ID."""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM tareas WHERE id = ?', (tarea_id,))
        self.conn.commit()

    def actualizar_descripcion(self, tarea_id: int, nueva_descripcion: str):
        """Modifica el texto de una tarea existente."""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE tareas SET descripcion = ? WHERE id = ?', (nueva_descripcion, tarea_id))
        self.conn.commit()    
        
    def cerrar_conexion(self):
        """Buena práctica para liberar el archivo cuando se cierra la app."""
        self.conn.close()