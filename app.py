from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Anet@2510",
    database="blog_db"
)
cursor = db.cursor(dictionary=True)

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            return redirect("/home")

        return "Invalid credentials"

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        pwd = generate_password_hash(request.form["password"])
        cursor.execute(
            "INSERT INTO users (username,email,password) VALUES (%s,%s,%s)",
            (request.form["username"], request.form["email"], pwd)
        )
        db.commit()

        # Insert default settings
        cursor.execute("INSERT INTO settings (user_id) VALUES (LAST_INSERT_ID())")
        db.commit()

        return redirect("/")

    return render_template("register.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- HOME / FEED ----------------
@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/")

    cursor.execute("""
        SELECT posts.*, users.username,
        (SELECT COUNT(*) FROM likes WHERE likes.post_id = posts.post_id) AS like_count
        FROM posts
        JOIN users ON posts.user_id = users.user_id
        ORDER BY posts.post_id DESC
    """)
    posts = cursor.fetchall()

    for post in posts:
        cursor.execute(
            "SELECT comments.comment, users.username FROM comments JOIN users ON comments.user_id=users.user_id WHERE comments.post_id=%s",
            (post["post_id"],)
        )
        post["comments"] = cursor.fetchall()

        cursor.execute(
            "SELECT * FROM likes WHERE post_id=%s AND user_id=%s",
            (post["post_id"], session["user_id"])
        )
        post["liked"] = cursor.fetchone()

    return render_template("home.html", posts=posts)

# ---------------- ADD POST ----------------
@app.route("/add_post", methods=["POST"])
def add_post():
    if "user_id" not in session:
        return redirect("/")

    cursor.execute(
        "INSERT INTO posts (user_id, title, content) VALUES (%s,%s,%s)",
        (session["user_id"], request.form["title"], request.form["content"])
    )
    db.commit()
    return redirect("/home")

# ---------------- EDIT POST ----------------
@app.route("/edit/<int:post_id>", methods=["GET","POST"])
def edit_post(post_id):
    if "user_id" not in session:
        return redirect("/")

    if request.method=="POST":
        cursor.execute(
            "UPDATE posts SET title=%s, content=%s WHERE post_id=%s AND user_id=%s",
            (request.form["title"], request.form["content"], post_id, session["user_id"])
        )
        db.commit()
        return redirect("/home")

    cursor.execute(
        "SELECT * FROM posts WHERE post_id=%s AND user_id=%s",
        (post_id, session["user_id"])
    )
    post = cursor.fetchone()
    return render_template("edit_post.html", post=post)

# ---------------- DELETE POST ----------------
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    if "user_id" not in session:
        return redirect("/")

    cursor.execute(
        "DELETE FROM posts WHERE post_id=%s AND user_id=%s",
        (post_id, session["user_id"])
    )
    db.commit()
    return redirect("/home")

# ---------------- LIKE ----------------
@app.route("/like/<int:post_id>")
def like(post_id):
    if "user_id" not in session:
        return redirect("/")

    try:
        cursor.execute(
            "INSERT INTO likes (post_id, user_id) VALUES (%s,%s)",
            (post_id, session["user_id"])
        )
        db.commit()
    except:
        pass
    return redirect("/home")

# ---------------- COMMENT ----------------
@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if "user_id" not in session:
        return redirect("/")

    cursor.execute(
        "INSERT INTO comments (post_id, user_id, comment) VALUES (%s,%s,%s)",
        (post_id, session["user_id"], request.form["comment"])
    )
    db.commit()
    return redirect("/home")

# ---------------- LIKES PAGE ----------------
@app.route("/likes")
def likes_page():
    if "user_id" not in session:
        return redirect("/")

    cursor.execute("""
        SELECT posts.*, users.username
        FROM posts
        JOIN likes ON posts.post_id = likes.post_id
        JOIN users ON posts.user_id = users.user_id
        WHERE likes.user_id=%s
        ORDER BY posts.post_id DESC
    """, (session["user_id"],))
    posts = cursor.fetchall()
    return render_template("likes.html", posts=posts)

# ---------------- SETTINGS ----------------
@app.route("/settings", methods=["GET","POST"])
def settings_page():
    if "user_id" not in session:
        return redirect("/")

    cursor.execute("SELECT * FROM settings WHERE user_id=%s", (session["user_id"],))
    settings = cursor.fetchone()

    if request.method=="POST":
        theme = request.form.get("theme","light")
        notifications = bool(request.form.get("notifications"))
        private_account = bool(request.form.get("private_account"))
        language = request.form.get("language","English")

        cursor.execute("""
            UPDATE settings SET theme=%s, notifications=%s, private_account=%s, language=%s
            WHERE user_id=%s
        """, (theme, notifications, private_account, language, session["user_id"]))
        db.commit()
        return redirect("/settings")

    return render_template("settings.html", settings=settings)

# ---------------- RUN APP ----------------
if __name__=="__main__":
    app.run(debug=True)

