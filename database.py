import os
import sqlite3

# ─────────────────────────────────────────────────
# Auto-detect: PostgreSQL on Render, SQLite locally
# ─────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    # Render gives postgres:// but psycopg2 needs postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    print("[Database]: Using PostgreSQL (Render Cloud Database)")
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), 'library.db')
    print("[Database]: Using SQLite (Local Development)")


# ─────────────────────────────────────────────────
# DictRow: Row wrapper — supports row['key'] AND row[0]
# ─────────────────────────────────────────────────
class DictRow:
    def __init__(self, row_tuple, col_names):
        self._tuple = row_tuple
        self._dict = dict(zip(col_names, row_tuple))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._tuple[key]
        return self._dict[key]

    def __iter__(self):
        return iter(self._tuple)

    def keys(self):
        return list(self._dict.keys())

    def get(self, key, default=None):
        return self._dict.get(key, default)


# ─────────────────────────────────────────────────
# UnifiedCursor: auto-converts ? → %s for PostgreSQL
# ─────────────────────────────────────────────────
class UnifiedCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def _fix_query(self, query):
        if USE_POSTGRES:
            query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            query = query.replace('AUTOINCREMENT', '')
            query = query.replace('?', '%s')
        return query

    def execute(self, query, params=()):
        self._cursor.execute(self._fix_query(query), params)

    def executemany(self, query, params_list):
        self._cursor.executemany(self._fix_query(query), params_list)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if USE_POSTGRES:
            cols = [d[0] for d in self._cursor.description]
            return DictRow(row, cols)
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        if USE_POSTGRES:
            cols = [d[0] for d in self._cursor.description]
            return [DictRow(r, cols) for r in rows]
        return rows


# ─────────────────────────────────────────────────
# UnifiedConnection: single interface for both DBs
# ─────────────────────────────────────────────────
class UnifiedConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return UnifiedCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_db_connection():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return UnifiedConnection(conn)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return UnifiedConnection(conn)


# ─────────────────────────────────────────────────
# init_db: Create tables + seed books (both DBs)
# ─────────────────────────────────────────────────
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Books Inventory Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Available',
            cover_style TEXT NOT NULL DEFAULT 'from-sky-500 to-indigo-600',
            icon TEXT NOT NULL DEFAULT '📘'
        )
    ''')

    # 2. Online Read Books Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reading_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT NOT NULL,
            read_url TEXT NOT NULL,
            description TEXT,
            cover_style TEXT NOT NULL DEFAULT 'from-sky-500 to-indigo-600',
            icon TEXT NOT NULL DEFAULT '📖'
        )
    ''')

    # 3. Admin Security Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_security (
            id INTEGER PRIMARY KEY,
            password TEXT NOT NULL,
            alternate_password TEXT NOT NULL
        )
    ''')
    conn.commit()

    # Seed books inventory if empty
    cursor.execute('SELECT COUNT(*) FROM books')
    if cursor.fetchone()[0] == 0:
        print("[Database]: Seeding inventory books...")
        seed_books = [
            # Entrepreneurs Section
            ('Shoe Dog', 'Phil Knight (Nike Creator)', 'Entrepreneurs', 'Available', 'from-purple-700 to-indigo-900', '👟'),
            ('Zero to One', 'Peter Thiel (PayPal Founder)', 'Entrepreneurs', 'Available', 'from-indigo-700 to-purple-900', '💡'),
            ('Elon Musk', 'Walter Isaacson', 'Entrepreneurs', 'Checked Out', 'from-purple-800 to-slate-900', '🚀'),
            ('The Lean Startup', 'Eric Ries', 'Entrepreneurs', 'Available', 'from-purple-600 to-indigo-800', '📈'),
            ('Steve Jobs', 'Walter Isaacson', 'Entrepreneurs', 'Available', 'from-slate-700 to-purple-900', '💻'),
            ('Principles: Life and Work', 'Ray Dalio (Bridgewater)', 'Entrepreneurs', 'Available', 'from-purple-700 to-violet-900', '💼'),

            # Philosophical Section
            ('Meditations', 'Marcus Aurelius', 'Philosophical', 'Available', 'from-violet-700 to-purple-900', '🏛️'),
            ('Beyond Good and Evil', 'Friedrich Nietzsche', 'Philosophical', 'Checked Out', 'from-purple-800 to-indigo-950', '🧠'),
            ('The Republic', 'Plato', 'Philosophical', 'Available', 'from-indigo-600 to-purple-800', '📜'),
            ('The Myth of Sisyphus', 'Albert Camus', 'Philosophical', 'Available', 'from-purple-900 to-slate-800', '⛰️'),

            # Technology & AI Section
            ('Life 3.0', 'Max Tegmark', 'Technology & AI', 'Available', 'from-indigo-600 to-purple-800', '🤖'),
            ('Clean Code', 'Robert C. Martin', 'Technology & AI', 'Available', 'from-purple-600 to-indigo-700', '💻'),
            ('The Pragmatic Programmer', 'David Thomas & Andrew Hunt', 'Technology & AI', 'Checked Out', 'from-violet-600 to-purple-900', '⚙️'),

            # Psychology & Mindset Section
            ('Atomic Habits', 'James Clear', 'Psychology & Mindset', 'Available', 'from-purple-600 to-fuchsia-700', '🎯'),
            ('Thinking, Fast and Slow', 'Daniel Kahneman', 'Psychology & Mindset', 'Available', 'from-purple-700 to-indigo-800', '🧩'),
            ('Deep Work', 'Cal Newport', 'Psychology & Mindset', 'Checked Out', 'from-fuchsia-700 to-purple-900', '⏳'),

            # Comics Section
            ('Watchmen', 'Alan Moore', 'Comics', 'Available', 'from-purple-500 to-pink-600', '⚡'),
            ('Batman: Year One', 'Frank Miller', 'Comics', 'Checked Out', 'from-purple-900 to-zinc-900', '🦇'),
            ('Spider-Man: Blue', 'Jeph Loeb', 'Comics', 'Available', 'from-indigo-600 to-purple-700', '🕷️'),
            ('Maus', 'Art Spiegelman', 'Comics', 'Available', 'from-violet-800 to-stone-900', '🎨')
        ]
        cursor.executemany('''
            INSERT INTO books (title, author, genre, status, cover_style, icon)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', seed_books)
        conn.commit()

    # Seed reading_books if empty
    cursor.execute('SELECT COUNT(*) FROM reading_books')
    if cursor.fetchone()[0] == 0:
        print("[Database]: Seeding digital read online books...")
        seed_reading_books = [
            ('Autobiography of Benjamin Franklin', 'Benjamin Franklin', 'Entrepreneurs',
             'https://www.gutenberg.org/ebooks/20203',
             'The timeless memoir of America\'s first great entrepreneur, scientist, and philosopher.',
             'from-amber-600 to-orange-800', '💼'),
            ('Think and Grow Rich', 'Napoleon Hill', 'Entrepreneurs',
             'https://archive.org/details/ThinkAndGrowRichPDF',
             'The foundational guide to financial success and entrepreneurial mindset.',
             'from-emerald-700 to-teal-900', '💰'),
            ('Principles for Navigating Big Debt Crises', 'Ray Dalio', 'Entrepreneurs',
             'https://www.principles.com/big-debt-crises/',
             'Free full digital edition by billionaire investor Ray Dalio.',
             'from-blue-700 to-indigo-900', '📊'),
            ('Meditations', 'Marcus Aurelius', 'Philosophical',
             'http://classics.mit.edu/Antoninus/meditations.html',
             'Personal private journal of the Roman Emperor with stoic wisdom.',
             'from-amber-700 to-yellow-900', '🏛️'),
            ('The Republic', 'Plato', 'Philosophical',
             'https://www.gutenberg.org/ebooks/1497',
             'Socrates\' dialogue exploring justice, governance, and the Allegory of the Cave.',
             'from-indigo-600 to-violet-800', '📜'),
            ('Beyond Good and Evil', 'Friedrich Nietzsche', 'Philosophical',
             'https://www.gutenberg.org/ebooks/4363',
             'A dramatic philosophical masterpiece challenging traditional morality.',
             'from-emerald-800 to-zinc-900', '🧠'),
            ('The Art of War', 'Sun Tzu', 'Philosophical',
             'https://www.gutenberg.org/ebooks/132',
             'Ancient military treatise on strategy and tactical superiority.',
             'from-red-800 to-amber-900', '⚔️'),
            ('Eloquent JavaScript (4th Edition)', 'Marijn Haverbeke', 'Technology & AI',
             'https://eloquentjavascript.net/',
             'Complete modern digital book on JavaScript and programming patterns.',
             'from-cyan-600 to-blue-700', '💻'),
            ('Automate the Boring Stuff with Python', 'Al Sweigart', 'Technology & AI',
             'https://automatetheboringstuff.com/',
             'Practical programming for beginners to automate daily workflows.',
             'from-sky-600 to-indigo-800', '🐍'),
            ('You Don\'t Know JS Yet', 'Kyle Simpson', 'Technology & AI',
             'https://github.com/getify/You-Dont-Know-JS',
             'Deep dive into the core mechanisms of JavaScript.',
             'from-yellow-600 to-amber-700', '⚡'),
            ('As a Man Thinketh', 'James Allen', 'Psychology & Mindset',
             'https://www.gutenberg.org/ebooks/4507',
             'A masterwork on the power of thought and mental attitude.',
             'from-purple-600 to-indigo-800', '🧩'),
            ('Self-Reliance', 'Ralph Waldo Emerson', 'Psychology & Mindset',
             'https://archive.org/details/selfreliance00emer',
             'Emerson\'s famous essay urging individuals to trust their intuition.',
             'from-emerald-600 to-green-800', '🌱'),
            ('Little Nemo in Slumberland Archive', 'Winsor McCay', 'Comics',
             'https://comicbookplus.com/?cid=1373',
             'Legendary vintage comic strip masterpiece with innovative visual layouts.',
             'from-amber-500 to-yellow-600', '🎨'),
            ('The Golden Age Comics Archive', 'Digital Comic Museum', 'Comics',
             'https://digitalcomicmuseum.com/',
             'Vast public domain archive of classic Golden Age comic books.',
             'from-slate-700 to-zinc-900', '⚡'),
            ('Alice\'s Adventures in Wonderland (Illustrated)', 'Lewis Carroll', 'Comics',
             'https://www.gutenberg.org/ebooks/11',
             'The world-famous illustrated classic fantasy adventure.',
             'from-pink-600 to-rose-800', '🐇')
        ]
        cursor.executemany('''
            INSERT INTO reading_books (title, author, genre, read_url, description, cover_style, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', seed_reading_books)
        conn.commit()
        print(f"[Database]: Successfully seeded {len(seed_reading_books)} online reading books.")

    # Seed admin security if empty
    cursor.execute('SELECT COUNT(*) FROM admin_security')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO admin_security (id, password, alternate_password)
            VALUES (1, ?, ?)
        ''', ('@books1234', 'bookslibrary'))
        conn.commit()
        print("[Database]: Initialized admin security table.")

    conn.close()


def get_security_credentials():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT password, alternate_password FROM admin_security WHERE id = 1')
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['password'], row['alternate_password']
    return '@books1234', 'bookslibrary'


def update_admin_password(new_password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE admin_security SET password = ? WHERE id = 1', (new_password,))
    conn.commit()
    conn.close()
    print("[Database]: Admin password updated successfully.")


if __name__ == '__main__':
    init_db()
