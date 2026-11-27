"""Orçamentos (RF-12 a RF-19)."""
import json

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..auth import perfil
from ..db import get_db, query
from ..regras import (SQL_TOTAL_ORC, RegraError, calcular_totais, converter_orcamento_em_os,
                      mudar_status_orcamento, proximo_seq, registrar_historico_orcamento,
                      salvar_itens_orcamento)
from ..util import agora_iso, codigo, hoje, hoje_iso, mais_dias, parse_int, parse_valor

bp = Blueprint("orcamentos", __name__, url_prefix="/orcamentos")

VALIDADES = [7, 15, 30, 60]
EDITAVEIS = {"rascunho", "enviado", "recusado"}


def get_orc(orc_id):
    o = query(f"SELECT o.*, {SQL_TOTAL_ORC} AS total FROM orcamentos o WHERE o.id = ?",
              (orc_id,), one=True)
    if o is None:
        abort(404)
    return o


@bp.route("/")
def lista():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    periodo = parse_int(request.args.get("periodo"), 0)
    sql = (f"SELECT o.*, c.nome AS cliente, {SQL_TOTAL_ORC} AS total FROM orcamentos o "
           "JOIN clientes c ON c.id = o.cliente_id WHERE 1=1")
    params = []
    if q:
        num = "".join(ch for ch in q if ch.isdigit())
        sql += " AND (c.nome LIKE ? OR o.descricao LIKE ?" + (" OR o.seq = ?" if num else "") + ")"
        params += [f"%{q}%", f"%{q}%"] + ([int(num)] if num else [])
    if status == "expirado":
        sql += " AND o.status = 'enviado' AND o.validade < ?"
        params.append(hoje_iso())
    elif status == "enviado":
        sql += " AND o.status = 'enviado' AND o.validade >= ?"
        params.append(hoje_iso())
    elif status:
        sql += " AND o.status = ?"
        params.append(status)
    if periodo:
        sql += " AND date(o.criado_em) >= ?"
        params.append(mais_dias(-periodo))
    sql += " ORDER BY o.seq DESC"
    orcs = query(sql, params)
    aguardando = query(f"SELECT COUNT(*) AS n, COALESCE(SUM({SQL_TOTAL_ORC}), 0) AS v FROM orcamentos o "
                       "WHERE o.status = 'enviado' AND o.validade >= ?", (hoje_iso(),), one=True)
    total = query("SELECT COUNT(*) AS n FROM orcamentos", one=True)["n"]
    return render_template("orcamentos/lista.html", orcs=orcs, q=q, status=status, periodo=periodo,
                           aguardando=aguardando, total=total)


def dados_formulario(itens=None):
    servicos = [dict(r) for r in query("SELECT id, descricao, preco FROM servicos WHERE ativo = 1 "
                                       "ORDER BY descricao")]
    pecas = [dict(id=r["id"], sku=r["sku"], descricao=r["descricao"], preco=r["preco"],
                  quantidade=r["quantidade"], minimo=r["estoque_minimo"])
             for r in query("SELECT * FROM itens_estoque ORDER BY descricao")]
    equips = {}
    for e in query("SELECT * FROM equipamentos ORDER BY tipo"):
        nome = e["tipo"] + (f" · {e['marca_modelo']}" if e["marca_modelo"] else "") + \
            (f" ({e['numero_serie']})" if e["numero_serie"] else "")
        equips.setdefault(str(e["cliente_id"]), []).append({"id": e["id"], "nome": nome})
    return {"servicos": servicos, "pecas": pecas, "equipamentos": equips, "itens": itens or []}


def ler_itens(raw):
    try:
        itens = json.loads(raw or "[]")
    except ValueError:
        raise RegraError("Não foi possível ler os itens do orçamento. Recarregue a página.")
    limpos = []
    for i in itens:
        tipo = i.get("tipo")
        desc = str(i.get("descricao") or "").strip()
        qtd = float(i.get("quantidade") or 0)
        vu = float(i.get("valor_unitario") or 0)
        if tipo not in ("servico", "peca", "avulso"):
            raise RegraError("Item com tipo inválido.")
        if not desc:
            raise RegraError("Preencha a descrição de todos os itens avulsos.")
        if qtd <= 0:
            raise RegraError(f"A quantidade de \"{desc}\" deve ser maior que zero.")
        if vu < 0:
            raise RegraError(f"O valor unitário de \"{desc}\" não pode ser negativo.")
        item_id = None
        if tipo == "peca":
            item_id = parse_int(i.get("item_estoque_id"))
            if not query("SELECT 1 FROM itens_estoque WHERE id = ?", (item_id,), one=True):
                raise RegraError(f"A peça \"{desc}\" não existe mais no estoque.")
            if qtd != int(qtd):
                raise RegraError(f"A quantidade da peça \"{desc}\" deve ser um número inteiro.")
        limpos.append({"tipo": tipo, "descricao": desc, "quantidade": qtd,
                       "valor_unitario": round(vu, 2), "item_estoque_id": item_id})
    if not limpos:
        raise RegraError("Adicione ao menos um serviço ou peça ao orçamento.")
    return limpos


def salvar(orc=None):
    """Cria ou atualiza o orçamento a partir do formulário. Devolve o id."""
    f = request.form
    cliente_id = parse_int(f.get("cliente_id"))
    cliente = query("SELECT * FROM clientes WHERE id = ?", (cliente_id,), one=True)
    if cliente is None:
        raise RegraError("Selecione um cliente cadastrado.")
    if cliente["status"] != "ativo":
        raise RegraError("O cliente selecionado está inativo. Reative o cadastro antes de orçar.")
    descricao = f.get("descricao", "").strip()
    if not descricao:
        raise RegraError("Informe a descrição do orçamento (ex.: Manutenção de notebook).")
    itens = ler_itens(f.get("itens_json"))
    desconto = parse_valor(f.get("desconto")) or 0
    calcular_totais(itens, desconto)            # valida RN-03
    dias = parse_int(f.get("validade_dias"), 15)
    validade = mais_dias(dias if dias in VALIDADES else 15)
    equip = parse_int(f.get("equipamento_id"))
    if equip and not query("SELECT 1 FROM equipamentos WHERE id = ? AND cliente_id = ?",
                           (equip, cliente_id), one=True):
        equip = None
    obs = f.get("observacoes", "").strip() or None
    status_novo = "rascunho" if f.get("acao") == "rascunho" else "enviado"

    db = get_db()
    with db:
        if orc is None:
            cur = db.execute(
                "INSERT INTO orcamentos (seq, cliente_id, equipamento_id, descricao, status, desconto, "
                "validade, observacoes, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (proximo_seq(db, "orcamentos"), cliente_id, equip, descricao, status_novo, desconto,
                 validade, obs, g.user["id"]))
            orc_id = cur.lastrowid
            registrar_historico_orcamento(db, orc_id, "rascunho", g.user["id"])
            if status_novo == "enviado":
                registrar_historico_orcamento(db, orc_id, "enviado", g.user["id"])
        else:
            orc_id = orc["id"]
            db.execute("UPDATE orcamentos SET cliente_id = ?, equipamento_id = ?, descricao = ?, "
                       "status = ?, desconto = ?, validade = ?, observacoes = ?, atualizado_em = ?, "
                       "atualizado_por = ? WHERE id = ?",
                       (cliente_id, equip, descricao, status_novo, desconto, validade, obs,
                        agora_iso(), g.user["id"], orc_id))
            if status_novo != orc["status"]:
                registrar_historico_orcamento(db, orc_id, status_novo, g.user["id"])
        salvar_itens_orcamento(db, orc_id, itens)
    return orc_id, status_novo


def render_form(orc=None, form=None, itens=None):
    clientes = query("SELECT id, nome, documento FROM clientes WHERE status = 'ativo' "
                     "ORDER BY nome COLLATE NOCASE")
    valores = form or {}
    if orc and not form:
        dias = (hoje().fromisoformat(orc["validade"]) - hoje()).days
        valores = {"cliente_id": str(orc["cliente_id"]), "descricao": orc["descricao"],
                   "desconto": f"{orc['desconto']:.2f}".replace(".", ","),
                   "observacoes": orc["observacoes"] or "",
                   "equipamento_id": str(orc["equipamento_id"] or ""),
                   "validade_dias": str(min(VALIDADES, key=lambda v: abs(v - dias)))}
    if not form and not orc:
        valores = {"cliente_id": request.args.get("cliente", ""), "validade_dias": "15"}
    return render_template("orcamentos/form.html", orc=orc, v=valores, clientes=clientes,
                           validades=VALIDADES,
                           dados=dados_formulario(itens))


@bp.route("/novo", methods=["GET", "POST"])
@perfil("admin", "atendente")
def novo():
    if request.method == "POST":
        try:
            orc_id, st = salvar()
        except RegraError as e:
            flash(str(e), "erro")
            return render_form(form=request.form, itens=_itens_do_form())
        flash("Rascunho salvo." if st == "rascunho" else
              "Orçamento criado e marcado como enviado ao cliente.", "ok")
        return redirect(url_for("orcamentos.detalhe", orc_id=orc_id))
    return render_form()


@bp.route("/<int:orc_id>/editar", methods=["GET", "POST"])
@perfil("admin", "atendente")
def editar(orc_id):
    orc = get_orc(orc_id)
    if orc["status"] not in EDITAVEIS:
        flash("Orçamentos aprovados ou já convertidos em OS não podem ser editados.", "erro")
        return redirect(url_for("orcamentos.detalhe", orc_id=orc_id))
    if request.method == "POST":
        try:
            salvar(orc)
        except RegraError as e:
            flash(str(e), "erro")
            return render_form(orc, form=request.form, itens=_itens_do_form())
        flash("Orçamento atualizado.", "ok")
        return redirect(url_for("orcamentos.detalhe", orc_id=orc_id))
    itens = [dict(r) for r in query("SELECT tipo, item_estoque_id, descricao, quantidade, "
                                    "valor_unitario FROM orcamento_itens WHERE orcamento_id = ?",
                                    (orc_id,))]
    return render_form(orc, itens=itens)


def _itens_do_form():
    try:
        return json.loads(request.form.get("itens_json") or "[]")
    except ValueError:
        return []


@bp.route("/<int:orc_id>")
def detalhe(orc_id):
    orc = get_orc(orc_id)
    cliente = query("SELECT * FROM clientes WHERE id = ?", (orc["cliente_id"],), one=True)
    itens = query("SELECT * FROM orcamento_itens WHERE orcamento_id = ? ORDER BY tipo DESC, id",
                  (orc_id,))
    historico = {h["status"]: h["data"] for h in
                 query("SELECT * FROM orcamento_historico WHERE orcamento_id = ? ORDER BY data",
                       (orc_id,))}
    os_row = query("SELECT id, seq FROM ordens_servico WHERE orcamento_id = ?", (orc_id,), one=True)
    equip = query("SELECT * FROM equipamentos WHERE id = ?", (orc["equipamento_id"],), one=True) \
        if orc["equipamento_id"] else None
    tecnicos = query("SELECT id, nome FROM usuarios WHERE ativo = 1 AND perfil IN ('tecnico', 'admin') "
                     "ORDER BY nome")
    alertas = {}
    for i in itens:
        if i["tipo"] == "peca":
            p = query("SELECT * FROM itens_estoque WHERE id = ?", (i["item_estoque_id"],), one=True)
            if p and p["quantidade"] < i["quantidade"]:
                alertas[i["id"]] = f"Só há {p['quantidade']} un. em estoque"
    subtotal = sum(i["quantidade"] * i["valor_unitario"] for i in itens)
    dias_validade = (hoje().fromisoformat(orc["validade"]) - hoje()).days
    return render_template("orcamentos/detalhe.html", orc=orc, cliente=cliente, itens=itens,
                           historico=historico, os_row=os_row, equip=equip, tecnicos=tecnicos,
                           subtotal=subtotal, dias_validade=dias_validade, alertas=alertas,
                           previsao_padrao=mais_dias(5))


@bp.route("/<int:orc_id>/status", methods=["POST"])
@perfil("admin", "atendente")
def mudar_status(orc_id):
    novo = request.form.get("status", "")
    db = get_db()
    try:
        with db:
            mudar_status_orcamento(db, orc_id, novo, g.user["id"])
        msgs = {"enviado": "Orçamento marcado como enviado ao cliente.",
                "aprovado": "Orçamento aprovado. Agora você pode gerar a ordem de serviço.",
                "recusado": "Orçamento marcado como recusado.",
                "rascunho": "Orçamento voltou para rascunho."}
        flash(msgs.get(novo, "Situação atualizada."), "ok")
    except RegraError as e:
        flash(str(e), "erro")
    return redirect(url_for("orcamentos.detalhe", orc_id=orc_id))


@bp.route("/<int:orc_id>/gerar-os", methods=["POST"])
def gerar_os(orc_id):
    get_orc(orc_id)
    db = get_db()
    try:
        with db:
            os_id = converter_orcamento_em_os(
                db, orc_id, g.user["id"], parse_int(request.form.get("responsavel_id")),
                request.form.get("previsao") or None)
    except RegraError as e:
        flash(str(e), "erro")
        return redirect(url_for("orcamentos.detalhe", orc_id=orc_id))
    flash("Ordem de serviço gerada a partir do orçamento. As peças foram baixadas do estoque.", "ok")
    return redirect(url_for("ordens.detalhe", os_id=os_id))


@bp.route("/<int:orc_id>/imprimir")
def imprimir(orc_id):
    """RF-19: versão para impressão / salvar em PDF pelo navegador."""
    orc = get_orc(orc_id)
    cliente = query("SELECT * FROM clientes WHERE id = ?", (orc["cliente_id"],), one=True)
    itens = query("SELECT * FROM orcamento_itens WHERE orcamento_id = ? ORDER BY tipo DESC, id",
                  (orc_id,))
    subtotal = sum(i["quantidade"] * i["valor_unitario"] for i in itens)
    return render_template("orcamentos/imprimir.html", orc=orc, cliente=cliente, itens=itens,
                           subtotal=subtotal, numero=codigo("ORC", orc["seq"]))
