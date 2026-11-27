"""Ordens de serviço (RF-20 a RF-27)."""
from flask import (Blueprint, abort, flash, g, jsonify, redirect, render_template, request,
                   url_for)

from ..db import get_db, query
from ..regras import (SQL_TOTAL_OS, RegraError, adicionar_item_os, concluir_os, mudar_status_os,
                      os_editavel, proximo_seq, remover_item_os, totais_os)
from ..util import FORMAS_PAGAMENTO, agora_iso, hoje_iso, mais_dias, parse_int, parse_valor

bp = Blueprint("ordens", __name__, url_prefix="/os")


def get_os(os_id):
    o = query("SELECT os.*, c.nome AS cliente, u.nome AS responsavel FROM ordens_servico os "
              "JOIN clientes c ON c.id = os.cliente_id LEFT JOIN usuarios u ON u.id = os.responsavel_id "
              "WHERE os.id = ?", (os_id,), one=True)
    if o is None:
        abort(404)
    return o


def tecnicos():
    return query("SELECT id, nome FROM usuarios WHERE ativo = 1 AND perfil IN ('tecnico', 'admin') "
                 "ORDER BY nome")


@bp.route("/")
def lista():
    modo = request.args.get("modo", "quadro")
    q = request.args.get("q", "").strip()
    resp = parse_int(request.args.get("responsavel"))
    status = request.args.get("status", "")
    sql = (f"SELECT os.*, c.nome AS cliente, u.nome AS responsavel, {SQL_TOTAL_OS} AS total "
           "FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id "
           "LEFT JOIN usuarios u ON u.id = os.responsavel_id WHERE 1=1")
    params = []
    if q:
        num = "".join(ch for ch in q if ch.isdigit())
        sql += " AND (c.nome LIKE ? OR os.titulo LIKE ?" + (" OR os.seq = ?" if num else "") + ")"
        params += [f"%{q}%", f"%{q}%"] + ([int(num)] if num else [])
    if resp:
        sql += " AND os.responsavel_id = ?"
        params.append(resp)
    if status and modo == "lista":
        sql += " AND os.status = ?"
        params.append(status)
    sql += " ORDER BY os.seq DESC"
    ordens = query(sql, params)
    colunas = {k: [o for o in ordens if o["status"] == k]
               for k in ("aberta", "andamento", "aguardando", "concluida")}
    total = query("SELECT COUNT(*) AS n FROM ordens_servico", one=True)["n"]
    return render_template("ordens/lista.html", ordens=ordens, colunas=colunas, modo=modo, q=q,
                           resp=resp, status=status, tecnicos=tecnicos(), total=total,
                           hoje=hoje_iso())


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    """RF-20: OS avulsa (sem orçamento)."""
    f = request.form if request.method == "POST" else {}
    if request.method == "POST":
        try:
            os_id = criar_avulsa(f)
        except RegraError as e:
            flash(str(e), "erro")
        else:
            flash("Ordem de serviço aberta.", "ok")
            return redirect(url_for("ordens.detalhe", os_id=os_id))
    clientes = query("SELECT id, nome FROM clientes WHERE status = 'ativo' ORDER BY nome COLLATE NOCASE")
    equips = {}
    for e in query("SELECT * FROM equipamentos"):
        equips.setdefault(str(e["cliente_id"]), []).append(
            {"id": e["id"], "tipo": e["tipo"], "modelo": e["marca_modelo"] or "",
             "serie": e["numero_serie"] or "",
             "nome": e["tipo"] + (f" · {e['marca_modelo']}" if e["marca_modelo"] else "")})
    v = dict(f) if f else {"cliente_id": request.args.get("cliente", ""),
                           "responsavel_id": str(g.user["id"]), "previsao": mais_dias(5)}
    return render_template("ordens/nova.html", clientes=clientes, tecnicos=tecnicos(), v=v,
                           equips=equips)


def criar_avulsa(f):
    cliente_id = parse_int(f.get("cliente_id"))
    cli = query("SELECT * FROM clientes WHERE id = ?", (cliente_id,), one=True)
    if cli is None:
        raise RegraError("Selecione o cliente da ordem de serviço.")
    if cli["status"] != "ativo":
        raise RegraError("O cliente está inativo. Reative o cadastro antes de abrir a OS.")
    titulo = f.get("titulo", "").strip()
    if not titulo:
        raise RegraError("Informe o serviço a realizar (ex.: Troca de SSD).")
    previsao = f.get("previsao") or None
    if previsao and previsao < hoje_iso():
        raise RegraError("A previsão não pode ser anterior à data de hoje.")
    tipo, modelo, serie = (f.get(k, "").strip() for k in ("equip_tipo", "equip_modelo", "equip_serie"))
    equip_id = parse_int(f.get("equipamento_id"))
    db = get_db()
    with db:
        if equip_id and not db.execute("SELECT 1 FROM equipamentos WHERE id = ? AND cliente_id = ?",
                                       (equip_id, cliente_id)).fetchone():
            equip_id = None
        if not equip_id and tipo:          # RF-10: guarda o equipamento para reaproveitar
            equip_id = db.execute("INSERT INTO equipamentos (cliente_id, tipo, marca_modelo, numero_serie) "
                                  "VALUES (?, ?, ?, ?)", (cliente_id, tipo, modelo or None,
                                                          serie or None)).lastrowid
        cur = db.execute(
            "INSERT INTO ordens_servico (seq, cliente_id, equipamento_id, titulo, equip_tipo, "
            "equip_modelo, equip_serie, equip_acessorios, problema, responsavel_id, abertura, "
            "previsao, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (proximo_seq(db, "ordens_servico"), cliente_id, equip_id, titulo, tipo or None,
             modelo or None, serie or None, f.get("equip_acessorios", "").strip() or None,
             f.get("problema", "").strip() or None, parse_int(f.get("responsavel_id")),
             hoje_iso(), previsao, g.user["id"]))
        db.execute("INSERT INTO os_historico (os_id, status, usuario_id) VALUES (?, 'aberta', ?)",
                   (cur.lastrowid, g.user["id"]))
    return cur.lastrowid


@bp.route("/<int:os_id>")
def detalhe(os_id):
    o = get_os(os_id)
    cliente = query("SELECT * FROM clientes WHERE id = ?", (o["cliente_id"],), one=True)
    itens = query("SELECT oi.*, ie.sku, ie.quantidade AS saldo FROM os_itens oi "
                  "LEFT JOIN itens_estoque ie ON ie.id = oi.item_estoque_id WHERE oi.os_id = ? "
                  "ORDER BY oi.id", (os_id,))
    orc = query("SELECT id, seq FROM orcamentos WHERE id = ?", (o["orcamento_id"],), one=True) \
        if o["orcamento_id"] else None
    conta = query("SELECT * FROM contas WHERE os_id = ?", (os_id,), one=True)
    historico = query("SELECT h.*, u.nome FROM os_historico h LEFT JOIN usuarios u ON u.id = h.usuario_id "
                      "WHERE h.os_id = ? ORDER BY h.data DESC, h.id DESC", (os_id,))
    servicos = query("SELECT * FROM servicos WHERE ativo = 1 ORDER BY descricao")
    pecas = query("SELECT * FROM itens_estoque ORDER BY descricao")
    return render_template("ordens/detalhe.html", o=o, cliente=cliente, itens=itens, orc=orc,
                           conta=conta, historico=historico, servicos=servicos, pecas=pecas,
                           tecnicos=tecnicos(), tot=totais_os(get_db(), os_id),
                           editavel=os_editavel(o, g.user["perfil"]),
                           vencimento_padrao=mais_dias(15))


def exigir_editavel(o):
    if not os_editavel(o, g.user["perfil"]):
        raise RegraError("Esta OS está concluída. Somente o administrador pode alterá-la (RN-09).")


@bp.route("/<int:os_id>/salvar", methods=["POST"])
def salvar(os_id):
    o = get_os(os_id)
    f = request.form
    try:
        exigir_editavel(o)
        desconto = parse_valor(f.get("desconto")) or 0
        bruto = totais_os(get_db(), os_id)
        if desconto < 0 or desconto > bruto["servicos"] + bruto["pecas"]:
            raise RegraError("O desconto não pode ser negativo nem maior que serviços + peças (RN-03).")
        db = get_db()
        with db:
            db.execute(
                "UPDATE ordens_servico SET titulo = ?, equip_tipo = ?, equip_modelo = ?, equip_serie = ?, "
                "equip_acessorios = ?, problema = ?, laudo = ?, observacoes = ?, responsavel_id = ?, "
                "previsao = ?, desconto = ?, atualizado_em = ?, atualizado_por = ? WHERE id = ?",
                (f.get("titulo", "").strip() or o["titulo"],
                 *(f.get(k, "").strip() or None for k in ("equip_tipo", "equip_modelo", "equip_serie",
                                                          "equip_acessorios", "problema", "laudo",
                                                          "observacoes")),
                 parse_int(f.get("responsavel_id")), f.get("previsao") or None, desconto,
                 agora_iso(), g.user["id"], os_id))
        flash("Ordem de serviço salva.", "ok")
    except RegraError as e:
        flash(str(e), "erro")
    return redirect(url_for("ordens.detalhe", os_id=os_id))


@bp.route("/<int:os_id>/itens", methods=["POST"])
def adicionar_item(os_id):
    o = get_os(os_id)
    f = request.form
    db = get_db()
    try:
        exigir_editavel(o)
        tipo = f.get("tipo")
        qtd = parse_valor(f.get("quantidade")) or 1
        if tipo == "peca":
            peca = query("SELECT * FROM itens_estoque WHERE id = ?", (parse_int(f.get("item_id")),), one=True)
            if peca is None:
                raise RegraError("Selecione um item do estoque.")
            with db:
                adicionar_item_os(db, os_id, "peca", peca["descricao"], qtd, peca["preco"],
                                  g.user["id"], peca["id"])
            novo = peca["quantidade"] - int(qtd)
            msg = f"Peça adicionada. Saldo de {peca['sku']}: {novo} un."
            if novo <= peca["estoque_minimo"]:
                flash(msg + " Atenção: estoque baixo.", "aviso")
            else:
                flash(msg, "ok")
        elif tipo == "servico":
            s = query("SELECT * FROM servicos WHERE id = ?", (parse_int(f.get("servico_id")),), one=True)
            if s is None:
                raise RegraError("Selecione um serviço.")
            with db:
                adicionar_item_os(db, os_id, "servico", s["descricao"], qtd, s["preco"], g.user["id"])
            flash("Serviço adicionado.", "ok")
        elif tipo == "avulso":
            desc = f.get("descricao", "").strip()
            valor = parse_valor(f.get("valor"))
            if not desc or valor is None or valor < 0:
                raise RegraError("Informe a descrição e o valor do item avulso.")
            with db:
                adicionar_item_os(db, os_id, "avulso", desc, qtd, valor, g.user["id"])
            flash("Item adicionado.", "ok")
        else:
            raise RegraError("Tipo de item inválido.")
    except RegraError as e:
        flash(str(e), "erro")
    return redirect(url_for("ordens.detalhe", os_id=os_id) + "#itens")


@bp.route("/<int:os_id>/itens/<int:item_id>/remover", methods=["POST"])
def remover_item(os_id, item_id):
    o = get_os(os_id)
    db = get_db()
    try:
        exigir_editavel(o)
        if not db.execute("SELECT 1 FROM os_itens WHERE id = ? AND os_id = ?", (item_id, os_id)).fetchone():
            abort(404)
        with db:
            remover_item_os(db, item_id, g.user["id"])
        flash("Item removido. Peças voltam automaticamente ao estoque.", "ok")
    except RegraError as e:
        flash(str(e), "erro")
    return redirect(url_for("ordens.detalhe", os_id=os_id) + "#itens")


@bp.route("/<int:os_id>/status", methods=["POST"])
def mudar_status(os_id):
    get_os(os_id)
    json_req = request.is_json
    novo = (request.get_json(silent=True) or {}).get("status") if json_req else request.form.get("status")
    db = get_db()
    try:
        with db:
            mudar_status_os(db, os_id, novo, g.user["id"], g.user["perfil"])
    except RegraError as e:
        if json_req:
            return jsonify(erro=str(e)), 400
        flash(str(e), "erro")
        return redirect(url_for("ordens.detalhe", os_id=os_id))
    if json_req:
        return jsonify(ok=True)
    flash("Situação da OS atualizada.", "ok")
    return redirect(url_for("ordens.detalhe", os_id=os_id))


@bp.route("/<int:os_id>/finalizar", methods=["POST"])
def finalizar(os_id):
    get_os(os_id)
    forma = request.form.get("forma_pagamento", "")
    if forma not in FORMAS_PAGAMENTO:
        flash("Selecione a forma de pagamento.", "erro")
        return redirect(url_for("ordens.detalhe", os_id=os_id, finalizar=1))
    db = get_db()
    try:
        with db:                                     # RNF-14: tudo ou nada
            laudo = request.form.get("laudo", "").strip()
            if laudo:
                db.execute("UPDATE ordens_servico SET laudo = ? WHERE id = ?", (laudo, os_id))
            conta_id = concluir_os(db, os_id, g.user["id"], forma, request.form.get("vencimento"))
    except RegraError as e:
        flash(str(e), "erro")
        return redirect(url_for("ordens.detalhe", os_id=os_id))
    if conta_id:
        flash("OS concluída. A conta a receber foi gerada no Financeiro.", "ok")
    else:
        flash("OS concluída. Sem valor a cobrar, nenhuma conta foi gerada.", "ok")
    return redirect(url_for("ordens.detalhe", os_id=os_id))
