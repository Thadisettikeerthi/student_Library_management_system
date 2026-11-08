import sys
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from database import get_db_connection, init_db, get_security_credentials, update_admin_password

# Configure stdout for utf-8 on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

app = Flask(__name__)
app.secret_key = 'library_system_role_secret_key_2026'

# Style mappings for newly added books based on genre (White & Purple Aesthetic)
GENRE_STYLES = {
    'Entrepreneurs': ('from-purple-700 to-indigo-900', '💼'),
    'Technology & AI': ('from-indigo-600 to-purple-800', '🤖'),
    'Psychology & Mindset': ('from-purple-600 to-fuchsia-700', '🧠'),
    'Philosophical': ('from-violet-700 to-purple-900', '🏛️'),
    'Comics': ('from-purple-500 to-pink-600', '⚡'),
    'Technical': ('from-indigo-500 to-purple-700', '💻')
}

CATEGORY_ORDER_SQL = '''
    CASE genre
        WHEN 'Entrepreneurs' THEN 1
        WHEN 'Technology & AI' THEN 2
        WHEN 'Psychology & Mindset' THEN 3
        WHEN 'Philosophical' THEN 4
        WHEN 'Comics' THEN 5
        ELSE 6
    END
'''

def normalize_genre(genre):
    if not genre:
        return 'All'
    g = genre.strip()
    if g.startswith('Technology'):
        return 'Technology & AI'
    if g.startswith('Psychology'):
        return 'Psychology & Mindset'
    return g

# ==========================================
# 🔑 AUTHENTICATION & LOGIN ROUTES
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if session.get('logged_in'):
            return redirect(url_for('index'))
        return render_template('index.html')
        
    data = request.get_json(silent=True) or request.form
    role = data.get('role', '').strip().lower()
    password = data.get('password', '').strip()
    
    if role == 'student':
        if password == 'student':
            session['logged_in'] = True
            session['role'] = 'Student'
            return jsonify({'success': True, 'redirect': url_for('index')})
        return jsonify({'success': False, 'message': 'Incorrect student password! Please try again.'}), 401
        
    elif role == 'admin':
        admin_pwd, _ = get_security_credentials()
        if password == admin_pwd:
            session['logged_in'] = True
            session['role'] = 'Admin'
            return jsonify({'success': True, 'redirect': url_for('index')})
        return jsonify({'success': False, 'message': 'Incorrect admin password! Please try again or use Forgot Password.'}), 401
        
    return jsonify({'success': False, 'message': 'Please select a valid role category (Student or Admin).'}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    raw_genre = request.args.get('genre', 'All')
    genre = normalize_genre(raw_genre)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch filtered or all books (ordered by section priority)
    if genre and genre != 'All':
        cursor.execute('SELECT * FROM books WHERE genre = ? ORDER BY id DESC', (genre,))
    else:
        cursor.execute(f'SELECT * FROM books ORDER BY {CATEGORY_ORDER_SQL}, id DESC')
    books = cursor.fetchall()
    
    # 2. Compute section-wise stats dictionary for each genre
    cursor.execute('''
        SELECT 
            genre, 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) as available,
            SUM(CASE WHEN status = 'Checked Out' THEN 1 ELSE 0 END) as checked_out
        FROM books 
        GROUP BY genre
    ''')
    genre_stats = {}
    for r in cursor.fetchall():
        genre_stats[r['genre']] = {
            'total': r['total'],
            'available': r['available'] or 0,
            'checked_out': r['checked_out'] or 0
        }
    
    # 3. Overall Library Counts
    cursor.execute('SELECT COUNT(*) FROM books')
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM books WHERE status = 'Available'")
    available_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM books WHERE status = 'Checked Out'")
    checked_out_count = cursor.fetchone()[0]
    
    # 4. Section-specific counts for the current active view
    if genre == 'All':
        section_total = total_count
        section_available = available_count
        section_checked_out = checked_out_count
    else:
        current_stat = genre_stats.get(genre, {'total': len(books), 'available': 0, 'checked_out': 0})
        section_total = current_stat['total']
        section_available = current_stat['available']
        section_checked_out = current_stat['checked_out']
        
    conn.close()
    
    return render_template(
        'dashboard.html',
        books=books,
        current_genre=genre,
        total_count=total_count,
        available_count=available_count,
        checked_out_count=checked_out_count,
        section_total=section_total,
        section_available=section_available,
        section_checked_out=section_checked_out,
        genre_stats=genre_stats,
        user_role=session.get('role', 'Student')
    )

@app.route('/add-book', methods=['POST'])
def add_book():
    if session.get('role') != 'Admin':
        return redirect(url_for('index'))
        
    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    genre = request.form.get('genre', 'Entrepreneurs').strip()
    current_genre = request.form.get('current_genre', 'All')
    
    if title and author:
        cover_style, icon = GENRE_STYLES.get(genre, ('from-purple-600 to-indigo-700', '📘'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO books (title, author, genre, status, cover_style, icon)
            VALUES (?, ?, ?, 'Available', ?, ?)
        ''', (title, author, genre, cover_style, icon))
        conn.commit()
        conn.close()
        print(f"[Backend]: Successfully inserted '{title}' by {author} into SQLite!")

    redirect_url = url_for('index')
    if current_genre != 'All':
        redirect_url += f"?genre={current_genre}"
    return redirect(redirect_url)

@app.route('/toggle-status/<int:book_id>', methods=['POST'])
def toggle_status(book_id):
    if session.get('role') != 'Admin':
        return redirect(url_for('index'))
        
    current_genre = request.form.get('genre', 'All')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT status, title FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book:
        new_status = 'Checked Out' if book['status'] == 'Available' else 'Available'
        cursor.execute('UPDATE books SET status = ? WHERE id = ?', (new_status, book_id))
        conn.commit()
        print(f"[Backend]: Toggled book ID {book_id} ('{book['title']}') to '{new_status}'.")
        
    conn.close()
    
    redirect_url = url_for('index')
    if current_genre != 'All':
        redirect_url += f"?genre={current_genre}"
    return redirect(redirect_url)

@app.route('/delete-book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if session.get('role') != 'Admin':
        return redirect(url_for('index'))
        
    current_genre = request.form.get('genre', 'All')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    print(f"[Backend]: Deleted book ID {book_id} from SQLite database.")
    
    redirect_url = url_for('index')
    if current_genre != 'All':
        redirect_url += f"?genre={current_genre}"
    return redirect(redirect_url)

# ==========================================
# 📖 READ BOOKS (ONLINE LIBRARY) ROUTES
# ==========================================

@app.route('/read-books')
def read_books():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    raw_genre = request.args.get('genre', 'All')
    genre = normalize_genre(raw_genre)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Order: Entrepreneurs FIRST, Technology & AI SECOND, then Psychology, Philosophical, Comics
    if genre and genre != 'All':
        cursor.execute('SELECT * FROM reading_books WHERE genre = ? ORDER BY id ASC', (genre,))
    else:
        cursor.execute(f'SELECT * FROM reading_books ORDER BY {CATEGORY_ORDER_SQL}, id ASC')
    reading_list = cursor.fetchall()
    
    cursor.execute('SELECT COUNT(*) FROM reading_books')
    total_reading = cursor.fetchone()[0]
    
    # Section-wise counts for reading books
    cursor.execute('SELECT genre, COUNT(*) as count FROM reading_books GROUP BY genre')
    reading_genre_counts = {r['genre']: r['count'] for r in cursor.fetchall()}
    
    conn.close()
    
    return render_template(
        'read_books.html',
        reading_books=reading_list,
        current_genre=genre,
        total_reading=total_reading,
        reading_genre_counts=reading_genre_counts,
        user_role=session.get('role', 'Student')
    )

@app.route('/add-reading-book', methods=['POST'])
def add_reading_book():
    if session.get('role') != 'Admin':
        return redirect(url_for('read_books'))
        
    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    genre = request.form.get('genre', 'Entrepreneurs').strip()
    read_url = request.form.get('read_url', '').strip()
    description = request.form.get('description', '').strip()
    current_genre = request.form.get('current_genre', 'All')
    
    if read_url and not read_url.startswith(('http://', 'https://')):
        read_url = 'https://' + read_url
        
    if title and author and read_url:
        cover_style, icon = GENRE_STYLES.get(genre, ('from-purple-600 to-indigo-700', '📖'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reading_books (title, author, genre, read_url, description, cover_style, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, author, genre, read_url, description, cover_style, icon))
        conn.commit()
        conn.close()
        print(f"[Backend]: Successfully added reading book '{title}' with link {read_url}")

    redirect_url = url_for('read_books')
    if current_genre != 'All':
        redirect_url += f"?genre={current_genre}"
    return redirect(redirect_url)

@app.route('/delete-reading-book/<int:book_id>', methods=['POST'])
def delete_reading_book(book_id):
    if session.get('role') != 'Admin':
        return redirect(url_for('read_books'))
        
    current_genre = request.form.get('genre', 'All')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reading_books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    print(f"[Backend]: Deleted reading book ID {book_id}")
    
    redirect_url = url_for('read_books')
    if current_genre != 'All':
        redirect_url += f"?genre={current_genre}"
    return redirect(redirect_url)

# ==========================================
# 🔒 ADMIN SECURITY & AUTHENTICATION ROUTES
# ==========================================

@app.route('/api/verify-password', methods=['POST'])
def verify_password():
    data = request.get_json(silent=True) or request.form
    pwd = data.get('password', '').strip()
    real_pwd, _ = get_security_credentials()
    
    if pwd == real_pwd:
        return jsonify({'success': True, 'message': 'Authentication successful!'})
    return jsonify({'success': False, 'message': 'Incorrect password! Please try again.'}), 401

@app.route('/api/verify-alternate-password', methods=['POST'])
def verify_alternate_password():
    data = request.get_json(silent=True) or request.form
    alt_pwd = data.get('alternate_password', '').strip()
    _, real_alt = get_security_credentials()
    
    if alt_pwd == real_alt:
        return jsonify({'success': True, 'message': 'Alternate password verified!'})
    return jsonify({'success': False, 'message': 'Invalid alternate password! Please try again.'}), 401

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json(silent=True) or request.form
    alt_pwd = data.get('alternate_password', '').strip()
    new_pwd = data.get('new_password', '').strip()
    
    _, real_alt = get_security_credentials()
    if alt_pwd != real_alt:
        return jsonify({'success': False, 'message': 'Invalid alternate password! Recovery authorization failed.'}), 401
    
    if not new_pwd:
        return jsonify({'success': False, 'message': 'New password cannot be empty!'}), 400
        
    update_admin_password(new_pwd)
    return jsonify({'success': True, 'message': 'Password has been successfully changed!'})

import os

# Always initialize DB on startup (works both locally and on Render)
init_db()

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    print("\n" + "=" * 50)
    print("🚀 Full-Stack Library Management System is RUNNING!")
    print(f"👉 Local Browser URL: http://localhost:{PORT}")
    print("💾 Database: SQLite (Persistent in 'library.db')")
    print("=" * 50 + "\n")
    app.run(host='0.0.0.0', port=PORT, debug=False)
