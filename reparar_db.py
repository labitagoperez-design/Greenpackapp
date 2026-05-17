import sqlite3
conn = sqlite3.connect('greenpack_v4.db')
conn.execute("DROP TABLE IF EXISTS ingreso_dia")
conn.close()
print("Tabla eliminada. Ahora intentá importar de nuevo.")