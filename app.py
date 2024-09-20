import os
import sqlite3
from flask import (
    Flask,
    flash,
    render_template,
    request,
    redirect,
    session,
    url_for,
    send_file,
)
from flask_cors import CORS
from io import BytesIO

app = Flask(__name__)
app.secret_key = "sua_chave_secreta_aqui"
CORS(app, supports_credentials=True)  # Ensuring CORS is properly set for all routes
frame_base_path = "frames"


# Function to connect to the database
def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn


# Function to create the database
def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            localidade TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
        """
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO users (username, password, localidade, is_admin)
        VALUES
        ('curitiba_user', 'senha_curitiba', 'curitiba', 0),
        ('sp_user', 'senha_sp', 'sp', 0),
        ('admin', 'admin', 'admin', 1)
        """
    )
    conn.commit()
    conn.close()


# Function to validate login
def check_login(username, password):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?", (username, password)
    ).fetchone()
    conn.close()
    if user:
        return user["localidade"], user["is_admin"]
    return None, None


# Function to update password and display the new password
def update_password(username, new_password):
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET password = ? WHERE username = ?", (new_password, username)
    )
    conn.commit()
    user = conn.execute(
        "SELECT password FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if user:
        updated_password = user["password"]
        print(f"The new password for {username} is: {updated_password}")


def add_user(username, password, localidade):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password, localidade) VALUES (?, ?, ?)",
            (username, password, localidade),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return False  # Retorna False se o usuário já existe
    conn.close()
    return True


def get_frame_path(localidade):
    frame_folder = os.path.join(frame_base_path, localidade)
    if not os.path.exists(frame_folder):
        try:
            os.makedirs(frame_folder)  # Ensure the directory is created
        except Exception as e:
            print(f"Failed to create directory {frame_folder}: {e}")
            return None
    return os.path.join(frame_folder, "current_frame.png")



# Route for login
@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    localidade, is_admin = check_login(username, password)
    if localidade:
        session["logged_in"] = True
        session["username"] = username
        session["localidade"] = localidade
        session["is_admin"] = is_admin
        if is_admin:
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("compartilhar_tela", username=username))
    return redirect(url_for("index"))


# Route for sharing screen
@app.route("/<username>/compartilhar-tela")
def compartilhar_tela(username):
    if "logged_in" in session and session.get("username") == username:
        localidade = session.get("localidade")
        share_link = url_for("view_screen_by_region", username=username, _external=True)
        return render_template(
            "tela-compartilhada.html",
            localidade=localidade,
            username=username,
            share_link=share_link,
        )
    return redirect(url_for("index"))


@app.route("/<username>/tela", endpoint="view_screen_by_region")
def view_screen_by_region(username):
    localidade = username  # Or retrieve 'localidade' from the database if needed
    return render_template("tela.html", regiao=localidade, username=username)


@app.route("/<localidade>/upload_frame", methods=["POST"])
def upload_frame(localidade):
    if "logged_in" in session and session.get("localidade") == localidade:
        if "frame" in request.files:
            frame = request.files["frame"]
            print(f"Frame received for {localidade}")
            frame_path = get_frame_path(localidade)
            if frame_path:
                try:
                    frame.save(frame_path)
                    print(f"Frame successfully saved at {frame_path}")
                except Exception as e:
                    print(f"Error saving frame: {e}")
                    return "", 500
            else:
                print(f"Invalid frame path for {localidade}")
                return "Failed to generate frame path", 500
        else:
            print("No frame received.")
        return "", 204
    return redirect(url_for("index"))



@app.route("/<username>/screen.png")
def serve_pil_image(username):
    frame_path = get_frame_path(username)
    if os.path.exists(frame_path):
        return send_file(frame_path, mimetype="image/png")
    else:
        return "Frame não encontrado.", 404




# Main page
@app.route("/")
def index():
    if "logged_in" in session:
        if session["is_admin"]:
            return redirect(url_for("admin_dashboard"))
        # Use "username" instead of "localidade"
        return redirect(url_for("compartilhar_tela", username=session["username"]))
    return render_template("login.html")


# Admin dashboard route
@app.route("/admin_dashboard")
def admin_dashboard():
    if "logged_in" in session and session["is_admin"]:
        return render_template("admin.html")
    return redirect(url_for("index"))


@app.route("/admin/manage_users")
def manage_users():
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        users = conn.execute(
            "SELECT * FROM users"
        ).fetchall()  # Fetch all users
        conn.close()
        return render_template("manage_users.html", users=users)
    else:
        return redirect(url_for("index"))


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if "logged_in" in session and session["is_admin"]:
        conn = get_db_connection()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        flash("User successfully deleted!", "success")
        return redirect(url_for("manage_users"))
    else:
        return redirect(url_for("index"))


@app.route("/admin/add_user", methods=["GET", "POST"])
def add_new_user():
    if "logged_in" in session and session["is_admin"]:
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            localidade = request.form["localidade"]
            if add_user(username, password, localidade):
                flash(
                    "User successfully added!", "success"
                )
            else:
                flash("Error: Username already exists!", "error")
            return redirect(url_for("admin_dashboard"))
        return render_template("add_user.html")


# Route for changing password
@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        username = request.form["username"]
        new_password = request.form["new_password"]
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        if user:
            update_password(username, new_password)
            return redirect("/")
        else:
            return "User not found."

    return render_template("change_password.html")


# Route for logging out
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# Error handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


# Initialize the database and start the app with external access
if __name__ == "__main__":
    create_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
