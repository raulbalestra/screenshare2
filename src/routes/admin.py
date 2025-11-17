"""
Rotas administrativas
"""
from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from src.database.models import UserManager
from werkzeug.security import check_password_hash

admin_bp = Blueprint('admin', __name__)


@admin_bp.route("/admin_dashboard")
def dashboard():
    """Painel do administrador"""
    if "logged_in" not in session or not session.get("is_admin"):
        return redirect(url_for("auth.index"))
    return render_template("admin.html")


@admin_bp.route("/admin/manage_users")
def manage_users():
    """Gerenciar usuários"""
    if "logged_in" not in session or not session.get("is_admin"):
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("auth.index"))
    
    users = UserManager.get_all_users()
    return render_template("manage_users.html", users=users)


@admin_bp.route("/admin/add_user", methods=["GET", "POST"])
def add_new_user():
    """Adicionar novo usuário"""
    if "logged_in" not in session or not session.get("is_admin"):
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("auth.index"))
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        localidade = request.form["localidade"]
        email = request.form.get("email") or username

        if not username or not password or not localidade:
            flash("Todos os campos são obrigatórios!", "error")
            return redirect(url_for("admin.add_new_user"))

        if UserManager.create_user(username, email, password, localidade):
            flash("Usuário adicionado com sucesso!", "success")
        else:
            flash("Erro: Nome de usuário já existe!", "error")
        
        return redirect(url_for("admin.manage_users"))

    return render_template("add_user.html")


@admin_bp.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    """Deletar usuário"""
    if "logged_in" not in session or not session.get("is_admin"):
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("auth.index"))
    
    if UserManager.delete_user(user_id):
        flash("Usuário excluído com sucesso!", "success")
    else:
        flash("Erro ao excluir usuário.", "error")
    
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/admin/block_user/<int:user_id>", methods=["POST"])
def block_user(user_id):
    """Bloquear usuário"""
    if "logged_in" not in session or not session.get("is_admin"):
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("auth.index"))
    
    if UserManager.update_user_status(user_id, False):
        flash("Usuário bloqueado com sucesso!", "success")
    else:
        flash("Erro ao bloquear o usuário.", "error")
    
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/admin/unblock_user/<int:user_id>", methods=["POST"])
def unblock_user(user_id):
    """Desbloquear usuário"""
    if "logged_in" not in session or not session.get("is_admin"):
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("auth.index"))
    
    if UserManager.update_user_status(user_id, True):
        flash("Usuário desbloqueado com sucesso!", "success")
    else:
        flash("Erro ao desbloquear o usuário.", "error")
    
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/admin/change_password/<int:user_id>", methods=["GET", "POST"])
def change_user_password(user_id):
    """Alterar senha de um usuário"""
    if "logged_in" not in session or not session.get("is_admin"):
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("auth.index"))
    
    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if not new_password or not confirm_password:
            flash("Ambos os campos de senha são obrigatórios.", "error")
            return redirect(url_for("admin.change_user_password", user_id=user_id))

        if new_password != confirm_password:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("admin.change_user_password", user_id=user_id))

        if UserManager.update_user_password(user_id, new_password):
            flash("Senha atualizada com sucesso.", "success")
            return redirect(url_for("admin.manage_users"))
        else:
            flash("Erro ao atualizar a senha.", "error")
            return redirect(url_for("admin.change_user_password", user_id=user_id))

    # Buscar informações do usuário para exibir no template
    users = UserManager.get_all_users()
    user = next((u for u in users if u[0] == user_id), None)
    
    if not user:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("admin.manage_users"))
    
    return render_template("admin_change_password.html", user=user)


@admin_bp.route("/admin/change_own_password", methods=["GET", "POST"])
def change_own_password():
    """Administrador alterar sua própria senha"""
    if "logged_in" not in session or not session.get("is_admin"):
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("auth.index"))
    
    if request.method == "POST":
        username = session.get("username")
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if not current_password or not new_password or not confirm_password:
            flash("Todos os campos são obrigatórios.", "error")
            return redirect(url_for("admin.change_own_password"))

        if new_password != confirm_password:
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("admin.change_own_password"))

        # Verificar senha atual
        localidade, is_admin = UserManager.authenticate_user(username, current_password)
        if not localidade:
            flash("Senha atual incorreta.", "error")
            return redirect(url_for("admin.change_own_password"))

        user_id = UserManager.get_user_id(username)
        if user_id and UserManager.update_user_password(user_id, new_password):
            flash("Senha atualizada com sucesso.", "success")
            return redirect(url_for("admin.dashboard"))
        else:
            flash("Erro ao atualizar a senha.", "error")
            return redirect(url_for("admin.change_own_password"))

    return render_template("admin_change_own_password.html")