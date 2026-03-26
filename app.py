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


# =========================================================
# LOGIN
# =========================================================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["role"] = user.get("role", "user")
            return redirect("/feed")

    return render_template("login.html")


# =========================================================
# REGISTER
# =========================================================
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


# =========================================================
# FEED (UPDATED WITH PROFILE PIC)
# =========================================================
@app.route("/feed")
def feed():
    if "user_id" not in session:
        return redirect("/")

    cursor.execute("""
        SELECT posts.*, users.username,
        settings.profile_pic,
        (SELECT COUNT(*) FROM likes WHERE likes.post_id = posts.post_id) AS like_count
        FROM posts
        JOIN users ON posts.user_id = users.user_id
        LEFT JOIN settings ON users.user_id = settings.user_id
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

    return render_template(
        "feed.html",
        posts=posts,
        comments_by_post=comments_by_post,
        user_id=session["user_id"]
    )


# =========================================================
# CREATE POST
# =========================================================
@app.route("/create", methods=["GET", "POST"])
def create():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        title = request.form.get("title", "")
        description = request.form.get("description", "")
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


# =========================================================
# SETTINGS (UPDATED WITH PROFILE PIC)
# =========================================================
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

        # 🔥 Handle Profile Picture Upload
        profile_pic = request.files.get("profile_pic")
        filename = None

        if profile_pic and profile_pic.filename != "":
            filename = secure_filename(profile_pic.filename)
            profile_pic.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        cursor.execute("""
            INSERT INTO settings (user_id, name, email, phone, bio, is_private, profile_pic)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
            name=%s, email=%s, phone=%s, bio=%s, is_private=%s,
            profile_pic = IF(%s IS NULL, profile_pic, %s)
        """, (
            user_id,name,email,phone,bio,is_private,filename,
            name,email,phone,bio,is_private,
            filename,filename
        ))
        db.commit()

    cursor.execute("SELECT * FROM settings WHERE user_id=%s", (user_id,))
    settings_data = cursor.fetchone()

    return render_template("settings.html", settings=settings_data)


# =========================================================
# CHANGE PASSWORD (NEW SEPARATE BAR)
# =========================================================
@app.route("/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect("/")

    current_password = request.form["current_password"]
    new_password = request.form["new_password"]
    confirm_password = request.form["confirm_password"]

    cursor.execute("SELECT password FROM users WHERE user_id=%s", (session["user_id"],))
    user = cursor.fetchone()

    if not check_password_hash(user["password"], current_password):
        return redirect("/settings")

    if new_password != confirm_password:
        return redirect("/settings")

    hashed = generate_password_hash(new_password)

    cursor.execute(
        "UPDATE users SET password=%s WHERE user_id=%s",
        (hashed, session["user_id"])
    )
    db.commit()

    return redirect("/settings")


# =========================================================
# LOGOUT
# =========================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =========================================================
if __name__ == "__main__":
    app.run(debug=True)