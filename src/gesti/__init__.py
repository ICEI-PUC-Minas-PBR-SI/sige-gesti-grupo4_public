"""GesTI - Sistema Integrado de Gestão para micro e pequenas empresas de serviços de TI."""
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, g, render_template

from . import auth, db, util


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.environ.get("GESTI_SECRET_KEY") or _chave_local(app.instance_path),
        DATABASE=os.environ.get("GESTI_DATABASE") or str(Path(app.instance_path) / "gesti.db"),
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),     # RNF-10
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("GESTI_HTTPS") == "1",
        CSRF_ENABLED=True,
        SEED_ON_CREATE=True,
        EMPRESA=os.environ.get("GESTI_EMPRESA", "NexaHertz"),
        EMPRESA_SIGLA=os.environ.get("GESTI_EMPRESA_SIGLA", "NH"),
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    util.register_filters(app)
    app.jinja_env.globals.update(csrf_token=auth.csrf_token, pode=auth.pode)

    with app.app_context():
        db.ensure_db()

    @app.before_request
    def _antes():
        auth.carregar_usuario()
        if app.config["CSRF_ENABLED"]:
            auth.verificar_csrf()
        return auth.exigir_login()

    @app.context_processor
    def _contadores():
        if not g.get("user"):
            return {}
        return {
            "nav_orcamentos": db.scalar(
                "SELECT COUNT(*) FROM orcamentos WHERE status = 'enviado' AND validade >= ?",
                (util.hoje_iso(),)),
            "nav_os": db.scalar("SELECT COUNT(*) FROM ordens_servico WHERE status <> 'concluida'"),
            "nav_alertas": db.scalar(
                "SELECT COUNT(*) FROM itens_estoque WHERE quantidade <= estoque_minimo"),
        }

    from .views import (busca, clientes, configuracoes, dashboard, estoque, financeiro,
                        orcamentos, ordens, relatorios)
    app.register_blueprint(auth.bp)
    for mod in (dashboard, clientes, orcamentos, ordens, estoque, financeiro, busca,
                relatorios, configuracoes):
        app.register_blueprint(mod.bp)

    for codigo_http, titulo, texto in (
        (400, "Requisição inválida", None),
        (403, "Acesso não permitido", "Seu perfil não tem permissão para esta área. "
                                      "Fale com o administrador se precisar de acesso."),
        (404, "Página não encontrada", "O registro ou a página que você procura não existe."),
    ):
        app.register_error_handler(codigo_http, _erro(codigo_http, titulo, texto))

    return app


def _erro(codigo_http, titulo, texto):
    def handler(e):
        msg = texto or getattr(e, "description", "") or ""
        return render_template("erro.html", codigo=codigo_http, titulo=titulo, texto=msg), codigo_http
    return handler


def _chave_local(instance_path: str) -> str:
    """Gera uma chave secreta por instalação, guardada fora do Git."""
    arq = Path(instance_path) / "secret_key"
    if not arq.exists():
        arq.write_text(secrets.token_hex(32), encoding="utf-8")
    return arq.read_text(encoding="utf-8").strip()
