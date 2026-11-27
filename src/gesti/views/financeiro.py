"""Financeiro: contas a receber e a pagar (RF-34 a RF-39, RF-43). Somente administrador (RF-02)."""
import csv
import io

from flask import (Blueprint, Response, flash, g, redirect, render_template, request, url_for)

from ..auth import perfil
from ..db import get_db, query
from ..regras import RegraError, marcar_conta_paga, proximo_seq
from ..util import (STATUS_CONTA, codigo, data_br, hoje_iso, parse_int, parse_valor,
                    status_conta)
from .dashboard import resumo_financeiro

bp = Blueprint("financeiro", __name__, url_prefix="/financeiro")


@bp.before_request
@perfil("admin")
def _somente_admin():
    return None


def filtrar(tipo, q, status, mes):
    sql = ("SELECT x.*, c.nome AS cliente, os.seq AS os_seq FROM contas x "
           "LEFT JOIN clientes c ON c.id = x.cliente_id "
           "LEFT JOIN ordens_servico os ON os.id = x.os_id WHERE x.tipo = ?")
    params = [tipo]
    if q:
        num = "".join(ch for ch in q if ch.isdigit())
        sql += " AND (x.descricao LIKE ? OR c.nome LIKE ? OR x.fornecedor LIKE ?" + \
               (" OR x.seq = ?" if num else "") + ")"
        params += [f"%{q}%"] * 3 + ([int(num)] if num else [])
    h = hoje_iso()
    if status == "pago":
        sql += " AND x.pago_em IS NOT NULL"
    elif status == "atraso":
        sql += " AND x.pago_em IS NULL AND x.vencimento < ?"
        params.append(h)
    elif status == "pendente":
        sql += " AND x.pago_em IS NULL AND x.vencimento >= ?"
        params.append(h)
    elif status == "aberto":
        sql += " AND x.pago_em IS NULL"
    if mes:
        sql += " AND substr(x.vencimento, 1, 7) = ?"
        params.append(mes)
    sql += " ORDER BY (x.pago_em IS NOT NULL), x.vencimento DESC, x.seq DESC"
    return query(sql, params)


@bp.route("/")
def lista():
    tipo = request.args.get("tipo", "receber")
    tipo = tipo if tipo in ("receber", "pagar") else "receber"
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    mes = request.args.get("mes", "")
    contas = filtrar(tipo, q, status, mes)
    n = {t: query("SELECT COUNT(*) AS n FROM contas WHERE tipo = ?", (t,), one=True)["n"]
         for t in ("receber", "pagar")}
    meses = [r[0] for r in query("SELECT DISTINCT substr(vencimento, 1, 7) FROM contas "
                                 "ORDER BY 1 DESC")]
    clientes = query("SELECT id, nome FROM clientes WHERE status = 'ativo' ORDER BY nome COLLATE NOCASE")
    return render_template("financeiro/lista.html", contas=contas, tipo=tipo, q=q, status=status,
                           mes=mes, meses=meses, n=n, fin=resumo_financeiro(),
                           total=sum(c["valor"] for c in contas), clientes=clientes)


@bp.route("/<int:conta_id>/pagar", methods=["POST"])
def pagar(conta_id):
    """RF-37: "Marcar como pago" com data e forma de pagamento."""
    db = get_db()
    tipo = request.form.get("tipo", "receber")
    try:
        with db:
            marcar_conta_paga(db, conta_id, request.form.get("data") or hoje_iso(),
                              request.form.get("forma_pagamento"), g.user["id"])
        flash("Pagamento registrado." if tipo == "pagar" else "Recebimento registrado.", "ok")
    except RegraError as e:
        flash(str(e), "erro")
    voltar = request.form.get("voltar", "")
    if not voltar.startswith("/") or voltar.startswith("//"):
        voltar = url_for("financeiro.lista", tipo=tipo)
    return redirect(voltar)


@bp.route("/nova", methods=["POST"])
def nova():
    """RF-35 (a pagar) e RF-36 (a receber avulsa)."""
    f = request.form
    tipo = f.get("tipo")
    try:
        if tipo not in ("receber", "pagar"):
            raise RegraError("Tipo de conta inválido.")
        desc = f.get("descricao", "").strip()
        valor = parse_valor(f.get("valor"))
        venc = f.get("vencimento", "")
        if not desc:
            raise RegraError("Informe a descrição da conta.")
        if valor is None or valor <= 0:
            raise RegraError("Informe um valor maior que zero, ex.: 289,90.")
        if not venc:
            raise RegraError("Informe o vencimento.")
        cliente_id = fornecedor = None
        if tipo == "receber":
            cliente_id = parse_int(f.get("cliente_id"))
            if not query("SELECT 1 FROM clientes WHERE id = ?", (cliente_id,), one=True):
                raise RegraError("Selecione o cliente da conta a receber.")
        else:
            fornecedor = f.get("fornecedor", "").strip()
            if not fornecedor:
                raise RegraError("Informe o fornecedor da conta a pagar.")
        db = get_db()
        with db:
            seq = proximo_seq(db, "contas", "tipo = ?", (tipo,))
            db.execute("INSERT INTO contas (tipo, seq, descricao, cliente_id, fornecedor, categoria, "
                       "valor, vencimento, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (tipo, seq, desc, cliente_id, fornecedor,
                        f.get("categoria") or ("Serviços" if tipo == "receber" else "Outros"),
                        valor, venc, g.user["id"]))
        flash(f"Conta {codigo('CR' if tipo == 'receber' else 'CP', seq)} lançada.", "ok")
    except RegraError as e:
        flash(str(e), "erro")
    return redirect(url_for("financeiro.lista", tipo=tipo if tipo in ("receber", "pagar") else "receber"))


@bp.route("/exportar.csv")
def exportar():
    """RF-43: exporta a listagem filtrada em CSV (abre no Excel)."""
    tipo = request.args.get("tipo", "receber")
    contas = filtrar(tipo if tipo in ("receber", "pagar") else "receber",
                     request.args.get("q", "").strip(), request.args.get("status", ""),
                     request.args.get("mes", ""))
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Título", "Descrição", "Cliente/Fornecedor", "Categoria", "Vencimento", "Valor",
                "Situação", "Pago em", "Forma de pagamento"])
    for c in contas:
        w.writerow([codigo("CR" if c["tipo"] == "receber" else "CP", c["seq"]), c["descricao"],
                    c["cliente"] or c["fornecedor"] or "", c["categoria"] or "",
                    data_br(c["vencimento"]), f"{c['valor']:.2f}".replace(".", ","),
                    STATUS_CONTA[status_conta(c)][0], data_br(c["pago_em"]) if c["pago_em"] else "",
                    c["forma_pagamento"] or ""])
    nome = f"contas-a-{tipo}-{hoje_iso()}.csv"
    return Response("﻿" + buf.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={nome}"})
