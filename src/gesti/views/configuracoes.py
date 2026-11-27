"""Configurações: usuários/perfis (RF-02) e catálogo de serviços. Somente administrador."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from ..auth import perfil
from ..db import get_db, query
from ..util import PERFIS, email_valido, parse_int, parse_valor

bp = Blueprint("configuracoes", __name__, url_prefix="/configuracoes")


@bp.before_request
@perfil("admin")
def _somente_admin():
    return None


@bp.route("/")
def index():
    usuarios = query("SELECT * FROM usuarios ORDER BY ativo DESC, nome")
    servicos = query("SELECT * FROM servicos ORDER BY ativo DESC, descricao")
    return render_template("configuracoes.html", usuarios=usuarios, servicos=servicos)


@bp.route("/usuarios", methods=["POST"])
def novo_usuario():
    f = request.form
    nome, email = f.get("nome", "").strip(), f.get("email", "").strip().lower()
    perfil_, senha = f.get("perfil"), f.get("senha", "")
    erro = None
    if not nome:
        erro = "Informe o nome do usuário."
    elif not email_valido(email):
        erro = "Informe um e-mail válido."
    elif perfil_ not in PERFIS:
        erro = "Selecione o perfil."
    elif len(senha) < 8:
        erro = "A senha deve ter pelo menos 8 caracteres."
    elif query("SELECT 1 FROM usuarios WHERE email = ?", (email,), one=True):
        erro = "Já existe um usuário com este e-mail."
    if erro:
        flash(erro, "erro")
    else:
        db = get_db()
        with db:
            db.execute("INSERT INTO usuarios (nome, email, senha_hash, perfil) VALUES (?, ?, ?, ?)",
                       (nome, email, generate_password_hash(senha), perfil_))
        flash(f"Usuário {nome} criado.", "ok")
    return redirect(url_for("configuracoes.index"))


@bp.route("/usuarios/<int:uid>", methods=["POST"])
def editar_usuario(uid):
    u = query("SELECT * FROM usuarios WHERE id = ?", (uid,), one=True)
    if u is None:
        abort(404)
    acao = request.form.get("acao")
    db = get_db()
    if uid == g.user["id"] and acao in ("ativo", "perfil"):
        flash("Você não pode desativar nem mudar o perfil do seu próprio usuário.", "erro")
        return redirect(url_for("configuracoes.index"))
    with db:
        if acao == "ativo":
            db.execute("UPDATE usuarios SET ativo = 1 - ativo WHERE id = ?", (uid,))
            flash("Usuário " + ("desativado." if u["ativo"] else "reativado."), "ok")
        elif acao == "perfil" and request.form.get("perfil") in PERFIS:
            db.execute("UPDATE usuarios SET perfil = ? WHERE id = ?", (request.form["perfil"], uid))
            flash("Perfil atualizado.", "ok")
        elif acao == "senha":
            senha = request.form.get("senha", "")
            if len(senha) < 8:
                flash("A nova senha deve ter pelo menos 8 caracteres.", "erro")
            else:
                db.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                           (generate_password_hash(senha), uid))
                flash(f"Senha de {u['nome']} redefinida.", "ok")
    return redirect(url_for("configuracoes.index"))


@bp.route("/servicos", methods=["POST"])
def servico():
    f = request.form
    sid = parse_int(f.get("id"))
    db = get_db()
    if f.get("acao") == "ativo" and sid:
        with db:
            db.execute("UPDATE servicos SET ativo = 1 - ativo WHERE id = ?", (sid,))
        flash("Serviço atualizado.", "ok")
        return redirect(url_for("configuracoes.index") + "#servicos")
    desc, preco = f.get("descricao", "").strip(), parse_valor(f.get("preco"))
    if not desc or preco is None or preco < 0:
        flash("Informe a descrição e o preço do serviço.", "erro")
    else:
        with db:
            db.execute("INSERT INTO servicos (descricao, preco) VALUES (?, ?)", (desc, preco))
        flash("Serviço adicionado ao catálogo.", "ok")
    return redirect(url_for("configuracoes.index") + "#servicos")
