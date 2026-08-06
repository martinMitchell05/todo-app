import sqlite3
import os

class Database:
    def __init__(self, db_path="data/tareas.db"):
        """Inicializa la conexión y asegura que la carpeta exista."""
        # Se asegura de crear la carpeta "data" si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Conecta a la base de datos (si el archivo no existe, lo crea)
        self.conn = sqlite3.connect(db_path)
        self.crear_tabla()

    def crear_tabla(self):
        """Crea la tabla principal si es la primera vez que se ejecuta."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descripcion TEXT NOT NULL,
                completada BOOLEAN NOT NULL CHECK (completada IN (0, 1)) DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def agregar_tarea(self, descripcion : str) -> int: 
        """Inserta una nueva tarea y devuelve su ID."""
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO tareas (descripcion) VALUES (?)', (descripcion,))
        self.conn.commit()
        return cursor.lastrowid # Te devuelve el ID por si lo necesitás en la interfaz

    def obtener_tareas(self) -> list:
        """Trae todas las tareas de la base de datos."""
        cursor = self.conn.cursor()
        # Por ahora traemos todo, después podemos filtrar por "completadas"
        cursor.execute('SELECT id, descripcion, completada FROM tareas ORDER BY fecha_creacion ASC')
        return cursor.fetchall()

    def marcar_como_completada(self, tarea_id: int):
        """Marca una tarea como completada."""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE tareas SET completada = 1 WHERE id = ?', (tarea_id,))
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