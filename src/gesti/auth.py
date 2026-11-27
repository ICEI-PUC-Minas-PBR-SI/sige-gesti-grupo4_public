"""Login, controle de acesso por perfil (RF-01, RF-02, RNF-11) e proteção CSRF."""
import secrets
from functools import wraps

from flask import (Blueprint, abort, flash, g, redirect, render_template, request, session,
                   url_for)
from werkzeug.security import check_password_hash

from .db import query

bp = Blueprint("auth", __name__)

ROTAS_PUBLICAS = {"auth.login", "static"}


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.get("user"):
        return redirect(url_for("dashboard.index"))
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        user = query("SELECT * FROM usuarios WHERE email = ? AND ativo = 1", (email,), one=True)
        if user is None or not check_password_hash(user["senha_hash"], senha):
            flash("E-mail ou senha incorretos. Confira os dados e tente novamente.", "erro")
        else:
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            destino = request.args.get("next")
            if not destino or not destino.startswith("/") or destino.startswith("//"):
                destino = url_for("dashboard.index")
            return redirect(destino)
    return render_template("login.html", email=email)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Você saiu do sistema.", "ok")
    return redirect(url_for("auth.login"))


def carregar_usuario():
    uid = session.get("user_id")
    g.user = None
    if uid is not None:
        g.user = query("SELECT * FROM usuarios WHERE id = ? AND ativo = 1", (uid,), one=True)
        if g.user is None:
            session.clear()


def exigir_login():
    if request.endpoint in ROTAS_PUBLICAS or request.endpoint is None:
        return None
    if g.user is None:
        if request.method == "GET":
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return redirect(url_for("auth.login"))
    return None


def perfil(*perfis):
    """Restringe a rota aos perfis informados. A checagem é no servidor (RNF-11)."""
    def deco(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None or g.user["perfil"] not in perfis:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return deco


def pode(acao: str) -> bool:
    """Permissões usadas nos templates para esconder o que o perfil não pode fazer."""
    p = g.user["perfil"] if g.get("user") else None
    regras = {
        "financeiro": {"admin"},
        "configuracoes": {"admin"},
        "relatorios": {"admin"},
        "editar_cliente": {"admin", "atendente"},
        "orcamento": {"admin", "atendente"},
        "estoque_editar": {"admin", "tecnico"},
    }
    return p in regras.get(acao, {"admin", "tecnico", "atendente"})


def csrf_token() -> str:
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def verificar_csrf():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        enviado = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not enviado or not secrets.compare_digest(enviado, session.get("_csrf", "")):
            abort(400, "Sessão expirada ou formulário inválido. Recarregue a página.")
