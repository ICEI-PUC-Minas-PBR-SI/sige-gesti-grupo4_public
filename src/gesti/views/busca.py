"""Busca global por clientes, OS e orçamentos (RF-03)."""
from flask import Blueprint, redirect, render_template, request, url_for

from ..db import query
from ..regras import SQL_TOTAL_ORC, SQL_TOTAL_OS
from ..util import so_digitos

bp = Blueprint("busca", __name__, url_prefix="/busca")


@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    if not q:
        return render_template("busca.html", q=q, clientes=[], oss=[], orcs=[], itens=[])
    like = f"%{q}%"
    up = q.upper().replace(" ", "")
    num = so_digitos(q)
    # atalho: "OS-0235" ou "ORC-0148" abre o registro direto
    if up.startswith(("OS-", "OS")) and num and not up.startswith("ORC"):
        o = query("SELECT id FROM ordens_servico WHERE seq = ?", (int(num),), one=True)
        if o:
            return redirect(url_for("ordens.detalhe", os_id=o["id"]))
    if up.startswith("ORC") and num:
        o = query("SELECT id FROM orcamentos WHERE seq = ?", (int(num),), one=True)
        if o:
            return redirect(url_for("orcamentos.detalhe", orc_id=o["id"]))

    clientes = query("SELECT * FROM clientes WHERE nome LIKE ? OR email LIKE ? OR contato LIKE ?"
                     + (" OR documento LIKE ?" if num else "") + " ORDER BY nome LIMIT 20",
                     [like, like, like] + ([f"%{num}%"] if num else []))
    oss = query(f"SELECT os.*, c.nome AS cliente, {SQL_TOTAL_OS} AS total FROM ordens_servico os "
                "JOIN clientes c ON c.id = os.cliente_id WHERE os.titulo LIKE ? OR c.nome LIKE ? "
                "OR os.equip_serie LIKE ? OR os.equip_modelo LIKE ?" + (" OR os.seq = ?" if num else "")
                + " ORDER BY os.seq DESC LIMIT 20",
                [like, like, like, like] + ([int(num)] if num else []))
    orcs = query(f"SELECT o.*, c.nome AS cliente, {SQL_TOTAL_ORC} AS total FROM orcamentos o "
                 "JOIN clientes c ON c.id = o.cliente_id WHERE o.descricao LIKE ? OR c.nome LIKE ?"
                 + (" OR o.seq = ?" if num else "") + " ORDER BY o.seq DESC LIMIT 20",
                 [like, like] + ([int(num)] if num else []))
    itens = query("SELECT * FROM itens_estoque WHERE descricao LIKE ? OR sku LIKE ? LIMIT 10",
                  (like, like))
    return render_template("busca.html", q=q, clientes=clientes, oss=oss, orcs=orcs, itens=itens)
