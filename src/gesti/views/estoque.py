"""Estoque (RF-28 a RF-33)."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..auth import perfil
from ..db import get_db, query, scalar
from ..regras import RegraError, gerar_sku, movimentar_estoque
from ..util import CATEGORIAS_ESTOQUE, agora_iso, parse_int, parse_valor

bp = Blueprint("estoque", __name__, url_prefix="/estoque")


def get_item(item_id):
    i = query("SELECT * FROM itens_estoque WHERE id = ?", (item_id,), one=True)
    if i is None:
        abort(404)
    return i


@bp.route("/")
def lista():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    cat = request.args.get("categoria", "")
    sql = "SELECT * FROM itens_estoque WHERE 1=1"
    params = []
    if q:
        sql += " AND (descricao LIKE ? OR sku LIKE ? OR fornecedor LIKE ?)"
        params += [f"%{q}%"] * 3
    if status == "ok":
        sql += " AND quantidade > estoque_minimo"
    elif status == "baixo":
        sql += " AND quantidade > 0 AND quantidade <= estoque_minimo"
    elif status == "zerado":
        sql += " AND quantidade = 0"
    elif status == "alerta":
        sql += " AND quantidade <= estoque_minimo"
    if cat:
        sql += " AND categoria = ?"
        params.append(cat)
    sql += " ORDER BY descricao COLLATE NOCASE"
    itens = query(sql, params)
    kpi = query("SELECT COUNT(*) AS n, COALESCE(SUM(quantidade * preco), 0) AS valor, "
                "SUM(quantidade > 0 AND quantidade <= estoque_minimo) AS baixo, "
                "SUM(quantidade = 0) AS zerado FROM itens_estoque", one=True)
    categorias = sorted(set(CATEGORIAS_ESTOQUE) | {r[0] for r in query(
        "SELECT DISTINCT categoria FROM itens_estoque")})
    return render_template("estoque/lista.html", itens=itens, kpi=kpi, q=q, status=status,
                           cat=cat, categorias=categorias)


def validar(f, item_id=None):
    d = {"descricao": f.get("descricao", "").strip(), "categoria": f.get("categoria", "").strip(),
         "sku": f.get("sku", "").strip().upper(), "fornecedor": f.get("fornecedor", "").strip() or None}
    erros = {}
    if not d["descricao"]:
        erros["descricao"] = "Informe a descrição do item."
    if not d["categoria"]:
        erros["categoria"] = "Selecione a categoria."
    d["estoque_minimo"] = parse_int(f.get("estoque_minimo"), -1)
    if d["estoque_minimo"] < 0:
        erros["estoque_minimo"] = "Informe o estoque mínimo (0 ou mais)."
    d["preco"] = parse_valor(f.get("preco"))
    if d["preco"] is None or d["preco"] < 0:
        erros["preco"] = "Informe o preço de venda, ex.: 219,90."
    if item_id is None:
        d["quantidade"] = parse_int(f.get("quantidade") or 0, -1)
        if d["quantidade"] < 0:
            erros["quantidade"] = "A quantidade inicial deve ser 0 ou mais."
    if d["sku"] and query("SELECT 1 FROM itens_estoque WHERE sku = ? AND id IS NOT ?",
                          (d["sku"], item_id), one=True):
        erros["sku"] = "Este SKU já existe. Deixe em branco para gerar automaticamente."
    return d, erros


@bp.route("/novo", methods=["GET", "POST"])
@perfil("admin", "tecnico")
def novo():
    d, erros = {"estoque_minimo": 1, "quantidade": 0}, {}
    if request.method == "POST":
        d, erros = validar(request.form)
        if not erros:
            db = get_db()
            with db:
                sku = d["sku"] or gerar_sku(db, d["descricao"])
                item_id = db.execute(
                    "INSERT INTO itens_estoque (sku, descricao, categoria, quantidade, estoque_minimo, "
                    "preco, fornecedor, criado_por) VALUES (?, ?, ?, 0, ?, ?, ?, ?)",
                    (sku, d["descricao"], d["categoria"], d["estoque_minimo"], d["preco"],
                     d["fornecedor"], g.user["id"])).lastrowid
                if d["quantidade"] > 0:
                    movimentar_estoque(db, item_id, "entrada", d["quantidade"],
                                       request.form.get("documento", "").strip() or "Saldo inicial",
                                       g.user["id"])
            flash(f"Item cadastrado com SKU {sku}.", "ok")
            return redirect(url_for("estoque.detalhe", item_id=item_id))
        flash("Corrija os campos destacados.", "erro")
    return render_template("estoque/form.html", i=d, erros=erros, novo=True,
                           categorias=CATEGORIAS_ESTOQUE)


@bp.route("/<int:item_id>/editar", methods=["GET", "POST"])
@perfil("admin", "tecnico")
def editar(item_id):
    i = get_item(item_id)
    erros = {}
    if request.method == "POST":
        d, erros = validar(request.form, item_id)
        if not erros:
            db = get_db()
            with db:
                db.execute("UPDATE itens_estoque SET sku = ?, descricao = ?, categoria = ?, "
                           "estoque_minimo = ?, preco = ?, fornecedor = ?, atualizado_em = ?, "
                           "atualizado_por = ? WHERE id = ?",
                           (d["sku"] or i["sku"], d["descricao"], d["categoria"], d["estoque_minimo"],
                            d["preco"], d["fornecedor"], agora_iso(), g.user["id"], item_id))
            flash("Item atualizado.", "ok")
            return redirect(url_for("estoque.detalhe", item_id=item_id))
        i = {**d, "id": item_id, "quantidade": i["quantidade"]}
        flash("Corrija os campos destacados.", "erro")
    return render_template("estoque/form.html", i=i, erros=erros, novo=False,
                           categorias=CATEGORIAS_ESTOQUE)


@bp.route("/<int:item_id>")
def detalhe(item_id):
    i = get_item(item_id)
    movs = query("SELECT m.*, os.seq AS os_seq, u.nome AS usuario FROM movimentacoes_estoque m "
                 "LEFT JOIN ordens_servico os ON os.id = m.os_id "
                 "LEFT JOIN usuarios u ON u.id = m.usuario_id WHERE m.item_id = ? "
                 "ORDER BY m.data DESC, m.id DESC", (item_id,))
    usado_em = scalar("SELECT COUNT(DISTINCT os_id) FROM os_itens WHERE item_estoque_id = ?", (item_id,))
    return render_template("estoque/detalhe.html", i=i, movs=movs, usado_em=usado_em)


@bp.route("/<int:item_id>/movimentar", methods=["POST"])
@perfil("admin", "tecnico")
def movimentar(item_id):
    """RF-30: entrada (com documento), saída e ajuste de inventário."""
    i = get_item(item_id)
    tipo = request.form.get("tipo_mov")
    qtd = parse_int(request.form.get("quantidade"))
    ref = request.form.get("referencia", "").strip()
    try:
        if tipo not in ("entrada", "saida", "ajuste"):
            raise RegraError("Escolha o tipo de movimentação.")
        if qtd is None or qtd < 0 or (qtd == 0 and tipo != "ajuste"):
            raise RegraError("Informe uma quantidade válida (número inteiro maior que zero).")
        if tipo == "entrada" and not ref:
            raise RegraError("Informe o documento da entrada (ex.: NF 4590 · Kingston).")
        delta = qtd if tipo == "entrada" else -qtd if tipo == "saida" else qtd - i["quantidade"]
        if tipo == "ajuste" and delta == 0:
            raise RegraError("O saldo informado é igual ao atual; nada a ajustar.")
        db = get_db()
        with db:
            saldo = movimentar_estoque(db, item_id, tipo, delta,
                                       ref or ("Ajuste de inventário" if tipo == "ajuste" else "Saída manual"),
                                       g.user["id"])
        flash(f"Movimentação registrada. Saldo atual: {saldo} un.", "ok")
    except RegraError as e:
        flash(str(e), "erro")
    return redirect(url_for("estoque.detalhe", item_id=item_id))
