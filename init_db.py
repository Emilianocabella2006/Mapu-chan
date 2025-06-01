import sqlite3
# Este script inicializa la base de datos SQLite para el sistema de foros

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
# Crear las tablas necesarias para el sistema de foros
cur.execute('''
CREATE TABLE IF NOT EXISTS boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE,
    name TEXT,
    description TEXT,
    banner TEXT
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id INTEGER,
    title TEXT,
    content TEXT,
    image TEXT,
    bump_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    sticky INTEGER DEFAULT 0,
    ip TEXT
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER,
    content TEXT,
    image TEXT,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip TEXT
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER,
    post_id INTEGER,
    reason TEXT,
    ip TEXT,
    date DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS post_log (
    ip TEXT,
    last_post_time DATETIME
)
''')



boards = [
    ('g', 'Generales'),
    ('v', 'Videojuegos'),
    ('a', 'Anime'),
    ('pol', 'Política'),
    ('t', 'Tecnología'),
    ('d', 'Deportes'),
    ('e', 'Entretenimiento'),
    ('int', 'Internacional'),
    ('nsfw', '+18')
]

conn.commit()
conn.close()

print("Base de datos inicializada.")