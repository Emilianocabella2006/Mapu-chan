from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, os
from datetime import datetime
from flask import flash
from werkzeug.utils import secure_filename
import re 
from markupsafe import Markup 
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random, string, io 
from flask import send_file 

App_secret_key = 'c3b0f8d1e2a4f5b6c7d8e9f0a1b2c3d4' 
MOD_KEY = '4196fecccd4ff648e000ca25b5f44171' 
app = Flask(__name__)
app.secret_key = App_secret_key

DB = 'db.sqlite3'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def query_db(query, args=(), one=False):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(query, args)
    rv = cur.fetchall()
    con.commit()
    con.close()
    return (rv[0] if rv else None) if one else rv



def parse_cites(text):
    if not text:
        return ''
    def replace(match):
        post_id = match.group(1)
        return f'<a href="#post-{post_id}" class="cite-link">&gt;&gt;{post_id}</a>'
    text = re.sub(r'>>(\d+)', replace, text)
    return Markup(text)


@app.route('/<board_slug>/', methods=['GET', 'POST'])
def board(board_slug):
    board = query_db('SELECT id, name FROM boards WHERE slug = ?', [board_slug], one=True)
    if not board:
        return "Board not found", 404
    board_id, board_name = board

    if request.method == 'POST':
        captcha_input = request.form.get('captcha')
        if captcha_input != session.get('captcha'):
            return "Captcha incorrecta", 400
        title = request.form['title']
        content = request.form['content']
        image = request.files.get('image')
        filename = None

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        query_db('INSERT INTO threads (board_id, title, content, image, bump_date) VALUES (?, ?, ?, ?, ?)',
                 [board_id, title, content, filename, datetime.now()])

    threads = query_db('SELECT id, title, sticky FROM threads WHERE board_id = ? ORDER BY sticky DESC, bump_date DESC', [board_id])
    return render_template('board.html', board_name=board_name, threads=threads, board_slug=board_slug)

@app.route('/<board_slug>/<int:thread_id>/', methods=['GET', 'POST'])
def thread(board_slug, thread_id):
    thread = query_db('SELECT title, content, image FROM threads WHERE id = ?', [thread_id], one=True)
    if not thread:
        return "Thread not found", 404

    if request.method == 'POST':
        content = request.form['content']
        image = request.files.get('image')
        filename = None

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        query_db('INSERT INTO posts (thread_id, content, image) VALUES (?, ?, ?)', [thread_id, content, filename])
        query_db('UPDATE threads SET bump_date = ? WHERE id = ?', [datetime.now(), thread_id])
        return redirect(url_for('thread', board_slug=board_slug, thread_id=thread_id))

    posts = query_db('SELECT id, content, image FROM posts WHERE thread_id = ?', [thread_id])
    return render_template('thread.html', thread=thread, posts=posts, board_slug=board_slug, thread_id=thread_id, parse_cites=parse_cites)

@app.route('/rules')
def rules():
    return render_template('rules.html')

@app.route('/')
def index():
    boards = query_db('SELECT slug, name FROM boards')
    threads = query_db('''
        SELECT id, board_id, title, content, image FROM threads
        ORDER BY bump_date DESC LIMIT 8
    ''')
    board_map = dict(query_db('SELECT id, slug FROM boards'))

    total_posts = query_db('SELECT COUNT(*) FROM posts', one=True)[0]
    total_threads = query_db('SELECT COUNT(*) FROM threads', one=True)[0]
    total_boards = len(boards)

    return render_template('index.html', boards=boards, threads=threads,
                           board_map=board_map,
                           total_posts=total_posts,
                           total_threads=total_threads,
                           total_boards=total_boards)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == MOD_KEY:
            if not session.get('moderator'):
                session['moderator'] = True
                flash('Has iniciado sesión como moderador')
            return redirect(url_for('mod_panel'))

        else:
            flash('Contraseña incorrecta')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('moderator', None)
    return redirect(url_for('index'))

@app.route('/mod')
def mod_panel():
    if not session.get('moderator'):
        return redirect(url_for('login'))
    posts = query_db('SELECT id, thread_id, content, image, date FROM posts ORDER BY date DESC')
    threads = query_db('SELECT id, board_id, title, content, image, bump_date FROM threads ORDER BY bump_date DESC')
    reports = query_db('SELECT id, thread_id, post_id, reason, date FROM reports ORDER BY date DESC')
    return render_template('mod_panel.html', posts=posts, threads=threads, reports=reports)


@app.route('/mod/delete_thread/<int:thread_id>')
def delete_thread(thread_id):
    if not session.get('moderator'):
        return redirect(url_for('login'))

    thread = query_db('SELECT image FROM threads WHERE id = ?', [thread_id], one=True)
    if thread and thread[0]:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], thread[0])
        if os.path.exists(image_path):
            os.remove(image_path)


    post_images = query_db('SELECT image FROM posts WHERE thread_id = ?', [thread_id])
    for post in post_images:
        if post[0]:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], post[0])
            if os.path.exists(image_path):
                os.remove(image_path)

    
    query_db('DELETE FROM posts WHERE thread_id = ?', [thread_id])
    query_db('DELETE FROM threads WHERE id = ?', [thread_id])
    return redirect(url_for('mod_panel'))


@app.route('/mod/delete_post/<int:post_id>')
def delete_post(post_id):
    if not session.get('moderator'):
        return redirect(url_for('login'))

    
    post = query_db('SELECT image FROM posts WHERE id = ?', [post_id], one=True)
    if post and post[0]:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], post[0])
        if os.path.exists(image_path):
            os.remove(image_path)

    
    query_db('DELETE FROM posts WHERE id = ?', [post_id])

    return redirect(url_for('mod_panel'))



@app.route('/report', methods=['GET', 'POST'])
def report():
    post_id = request.args.get('post_id')
    thread_id = request.args.get('thread_id')
    board_slug = request.args.get('board_slug')

    if request.method == 'POST':
        reason = request.form['reason']
        thread_id = request.form['thread_id']
        post_id = request.form['post_id']
        board_slug = request.form['board_slug']
        query_db('INSERT INTO reports (thread_id, post_id, reason) VALUES (?, ?, ?)', [thread_id, post_id, reason])
        return redirect(url_for('thread', board_slug=board_slug, thread_id=thread_id))

    return render_template('report.html', post_id=post_id, thread_id=thread_id, board_slug=board_slug)

@app.route('/mod/sticky/<int:thread_id>')
def toggle_sticky(thread_id):
    if not session.get('moderator'):
        return redirect(url_for('login'))

    current = query_db('SELECT sticky FROM threads WHERE id = ?', [thread_id], one=True)
    new_value = 0 if current[0] else 1
    query_db('UPDATE threads SET sticky = ? WHERE id = ?', [new_value, thread_id])
    return redirect(url_for('mod_panel'))

@app.route('/captcha')
def captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    session['captcha'] = text

    img = Image.new('RGB', (150, 50), (230, 230, 230))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 36)
    except:
        font = ImageFont.load_default()

    draw.text((10, 5), text, font=font, fill=(0, 0, 0))
    draw.line([(0, 0), (150, 50)], fill=(0, 0, 0), width=2)

    img = img.filter(ImageFilter.GaussianBlur(1))

    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')

@app.template_filter('parse_cites')
def parse_cites(text):
    if not text:
        return ''
    
    def replacer(match):
        post_id = match.group(1)
        return f'<a href="#post-{post_id}" class="cite-link">&gt;&gt;{post_id}</a>'
    
    replaced = re.sub(r'>>(\d+)', replacer, text)
    return

@app.template_filter('parse_cites')
def parse_cites(text):
    if not text:
        return ''
    
    def replacer(match):
        post_id = match.group(1)
        return f'<a href="#post-{post_id}" class="cite-link">&gt;&gt;{post_id}</a>'
    
    replaced = re.sub(r'>>(\d+)', replacer, text)
    return Markup(replaced)

if __name__ == '__main__':
    app.run()