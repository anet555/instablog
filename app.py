from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- Database ----------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Anet@2510",
    database="blog_db"
)
cursor = db.cursor(dictionary=True)

# ---------- Upload Folder ----------
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            return redirect("/feed")
    return render_template("login.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        pwd = generate_password_hash(request.form["password"])
        cursor.execute(
            "INSERT INTO users (username,email,password) VALUES (%s,%s,%s)",
            (request.form["username"], request.form["email"], pwd)
        )
        db.commit()
        return redirect("/")
    return render_template("register.html")

# ---------- FEED ----------
@app.route("/feed")
def feed():
    if "user_id" not in session:
        return redirect("/")

    cursor.execute("""
        SELECT posts.*, users.username,
        (SELECT COUNT(*) FROM likes WHERE likes.post_id = posts.post_id) AS like_count
        FROM posts
        JOIN users ON posts.user_id = users.user_id
        ORDER BY posts.created_at DESC
    """)
    posts = cursor.fetchall()

    cursor.execute("""
        SELECT comments.*, users.username FROM comments
        JOIN users ON comments.user_id = users.user_id
    """)
    comments = cursor.fetchall()
    comments_by_post = {}
    for c in comments:
        comments_by_post.setdefault(c['post_id'], []).append(c)

    return render_template("feed.html", posts=posts, comments_by_post=comments_by_post, user_id=session["user_id"])

# ---------- CREATE POST ----------
@app.route("/create", methods=["GET", "POST"])
def create():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        title = request.form.get("title", "")
        description = request.form.get("description", "")  # <- FIXED
        image = request.files.get("image")
        filename = None
        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        cursor.execute(
            "INSERT INTO posts (user_id, title, description, image) VALUES (%s,%s,%s,%s)",
            (session["user_id"], title, description, filename)
        )
        db.commit()
        return redirect("/feed")

    return render_template("create.html")

# ---------- EDIT POST ----------
@app.route("/edit_post/<int:post_id>", methods=["GET","POST"])
def edit_post(post_id):
    if "user_id" not in session:
        return redirect("/")

    cursor.execute("SELECT * FROM posts WHERE post_id=%s AND user_id=%s", (post_id, session["user_id"]))
    post = cursor.fetchone()
    if not post:
        return redirect("/feed")

    if request.method == "POST":
        title = request.form.get("title", "")
        description = request.form.get("description", "")  # <- FIXED
        image = request.files.get("image")
        filename = post["image"]
        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        cursor.execute(
            "UPDATE posts SET title=%s, description=%s, image=%s WHERE post_id=%s",
            (title, description, filename, post_id)
        )
        db.commit()
        return redirect("/feed")

    return render_template("edit_post.html", post=post)

# ---------- DELETE POST ----------
@app.route("/delete_post/<int:post_id>")
def delete_post(post_id):
    if "user_id" not in session:
        return redirect("/")

    cursor.execute("DELETE FROM posts WHERE post_id=%s AND user_id=%s", (post_id, session["user_id"]))
    db.commit()
    return redirect("/feed")

# ---------- LIKE POST ----------
@app.route("/like/<int:post_id>")
def like(post_id):
    if "user_id" not in session:
        return redirect("/")
    try:
        cursor.execute("INSERT INTO likes (post_id,user_id) VALUES (%s,%s)", (post_id, session["user_id"]))
        db.commit()
    except:
        pass
    return redirect("/feed")

# ---------- COMMENT POST ----------
@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if "user_id" not in session:
        return redirect("/")
    text = request.form["comment"]
    cursor.execute(
        "INSERT INTO comments (post_id,user_id,comment) VALUES (%s,%s,%s)",
        (post_id, session["user_id"], text)
    )
    db.commit()
    return redirect("/feed")

# ---------- SETTINGS ----------
@app.route("/settings", methods=["GET","POST"])
def settings():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        bio = request.form["bio"]
        private = request.form.get("private")
        is_private = True if private=="on" else False

        cursor.execute("""
            INSERT INTO settings (user_id, name, email, phone, bio, is_private)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
            name=%s, email=%s, phone=%s, bio=%s, is_private=%s
        """,(user_id,name,email,phone,bio,is_private,name,email,phone,bio,is_private))
        db.commit()

    cursor.execute("SELECT * FROM settings WHERE user_id=%s", (user_id,))
    settings_data = cursor.fetchone()
    return render_template("settings.html", settings=settings_data)

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)