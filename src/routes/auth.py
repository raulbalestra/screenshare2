"""
Rotas de autenticação e usuários
"""
from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from src.database.models import UserManager

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/")
def index():
    """Página principal - redireciona baseado no status de login"""
    if "logged_in" in session:
        if session["is_admin"]:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("rooms.dashboard"))
    return render_template("login.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Página e processamento de login"""
    if request.method == "GET":
        # Se já estiver logado, redireciona
        if "logged_in" in session:
            if session.get("is_admin"):
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("rooms.dashboard"))
        return render_template("login.html")
    
    # POST - Processa o login
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    
    if not username or not password:
        flash("Por favor, preencha todos os campos.", "error")
        return render_template("login.html")
    
    try:
        localidade, is_admin = UserManager.authenticate_user(username, password)
        
        if localidade == "blocked":
            flash("Seu acesso foi bloqueado pelo administrador.", "error")
            return render_template("login.html")
        elif localidade:
            session["logged_in"] = True
            session["username"] = username
            session["localidade"] = localidade
            session["is_admin"] = is_admin
            
            flash(f"Bem-vindo(a), {username}!", "success")
            
            if is_admin:
                return redirect(url_for("admin.dashboard"))
            else:
                return redirect(url_for("rooms.dashboard"))
        else:
            flash("Nome de usuário ou senha inválidos.", "error")
            return render_template("login.html")
    except Exception as e:
        print(f"Erro no login: {e}")
        flash("Erro interno do servidor. Tente novamente.", "error")
        return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Faz logout do usuário"""
    session.clear()
    return redirect(url_for("auth.index"))


@auth_bp.route("/change_password", methods=["GET", "POST"])
def change_password():
    """Permite ao usuário alterar sua própria senha"""
    if "logged_in" not in session:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("auth.index"))
    
    if request.method == "POST":
        username = session.get("username")
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if not new_password or not confirm_password:
            flash("Ambos os campos de senha são obrigatórios.", "error")
            return redirect(url_for("auth.change_password"))

        if new_password != confirm_password:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("auth.change_password"))

        user_id = UserManager.get_user_id(username)
        if user_id and UserManager.update_user_password(user_id, new_password):
            flash("Senha atualizada com sucesso.", "success")
            return redirect(url_for("auth.index"))
        else:
            flash("Erro ao atualizar a senha.", "error")
            return redirect(url_for("auth.change_password"))

    return render_template("change_password.html")