"""Conexão com o banco SQLite e criação do esquema."""
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

SCHEMA = Path(__file__).with_name("schema.sql")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def query(sql, params=(), one=False):
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def scalar(sql, params=()):
    row = get_db().execute(sql, params).fetchone()
    return row[0] if row else None


def init_db(seed: bool = True):
    """Recria o banco do zero (apaga os dados existentes)."""
    db = get_db()
    tables = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    db.execute("PRAGMA foreign_keys = OFF")
    for t in tables:
        db.execute(f'DROP TABLE IF EXISTS "{t}"')
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA.read_text(encoding="utf-8"))
    if seed:
        from .seed import seed_db
        seed_db(db)
    db.commit()


def ensure_db():
    """Cria e popula o banco na primeira execução."""
    path = Path(current_app.config["DATABASE"])
    if not path.exists() or path.stat().st_size == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        init_db(seed=current_app.config.get("SEED_ON_CREATE", True))


@click.command("init-db")
@click.option("--sem-dados", is_flag=True, help="Cria o banco vazio, sem dados de exemplo.")
def init_db_command(sem_dados):
    """Apaga e recria o banco de dados."""
    init_db(seed=not sem_dados)
    click.echo("Banco de dados recriado.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
