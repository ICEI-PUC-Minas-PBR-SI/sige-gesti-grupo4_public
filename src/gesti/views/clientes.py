"""Clientes (RF-05 a RF-11)."""
import json

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..auth import perfil
from ..db import get_db, query, scalar
from ..regras import SQL_TOTAL_ORC, SQL_TOTAL_OS
from ..util import (UFS, agora_iso, cep_valido, codigo, documento_valido, email_valido,
                    fmt_documento, moeda, so_digitos, telefone_valido)

bp = Blueprint("clientes", __name__, url_prefix="/clientes")

CAMPOS = ["nome", "documento", "contato", "email", "telefone", "cep", "endereco", "numero",
          "complemento", "cidade", "uf", "status", "anotacoes"]

EXEMPLO = {
    "nome": "Escola Nova Geração Ltda.", "documento": "11.444.777/0001-61",
    "contato": "Paula Andrade", "email": "ti@novageracao.edu.br", "telefone": "(31) 98888-1234",
    "cep": "30130-110", "endereco": "Av. Afonso Pena", "numero": "867", "complemento": "Sala 1201",
    "cidade": "Belo Horizonte", "uf": "MG",
}


def get_cliente(cliente_id):
    c = query("SELECT * FROM clientes WHERE id = ?", (cliente_id,), one=True)
    if c is None:
        abort(404)
    return c


def validar(form, cliente_id=None):
    """RF-06: valida formatos e impede CPF/CNPJ duplicado. Mensagens indicam o campo (RNF-04)."""
    d = {k: (form.get(k) or "").strip() for k in CAMPOS}
    erros = {}
    if not d["nome"]:
        erros["nome"] = "Informe o nome ou a razão social."
    doc = so_digitos(d["documento"])
    if doc:
        if not documento_valido(doc):
            erros["documento"] = ("CPF inválido. Confira os 11 dígitos." if len(doc) == 11 else
                                  "CNPJ inválido. Confira os 14 dígitos." if len(doc) == 14 else
                                  "Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).")
        else:
            outro = query("SELECT id, nome FROM clientes WHERE documento = ? AND id IS NOT ?",
                          (doc, cliente_id), one=True)
            if outro:
                erros["documento"] = f"Este CPF/CNPJ já está cadastrado para \"{outro['nome']}\"."
    d["documento"] = doc or None
    if d["email"] and not email_valido(d["email"]):
        erros["email"] = "E-mail inválido. Use o formato nome@empresa.com.br."
    d["email"] = d["email"].lower() or None
    if d["telefone"] and not telefone_valido(d["telefone"]):
        erros["telefone"] = "Telefone inválido. Informe DDD + número, ex.: (11) 90000-0000."
    d["telefone"] = so_digitos(d["telefone"]) or None
    if d["cep"] and not cep_valido(d["cep"]):
        erros["cep"] = "CEP inválido. Use 8 dígitos, ex.: 01310-100."
    d["cep"] = so_digitos(d["cep"]) or None
    if d["uf"] and d["uf"] not in UFS:
        erros["uf"] = "Selecione um estado válido."
    d["status"] = "inativo" if d["status"] == "inativo" else "ativo"
    return d, erros


@bp.route("/")
def lista():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    cidade = request.args.get("cidade", "")
    sql = ("SELECT c.*, "
           "(SELECT COUNT(*) FROM ordens_servico WHERE cliente_id = c.id AND status <> 'concluida') AS os_abertas, "
           "(SELECT MAX(d) FROM (SELECT MAX(abertura) AS d FROM ordens_servico WHERE cliente_id = c.id "
           " UNION ALL SELECT MAX(date(criado_em)) FROM orcamentos WHERE cliente_id = c.id)) AS ultimo "
           "FROM clientes c WHERE 1=1")
    params = []
    if q:
        sql += " AND (c.nome LIKE ? OR c.email LIKE ? OR c.contato LIKE ? OR c.documento LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like, f"%{so_digitos(q) or q}%"]
    if status in ("ativo", "inativo"):
        sql += " AND c.status = ?"
        params.append(status)
    if cidade:
        sql += " AND c.cidade = ?"
        params.append(cidade)
    sql += " ORDER BY c.status, c.nome COLLATE NOCASE"
    clientes = query(sql, params)
    total = scalar("SELECT COUNT(*) FROM clientes")
    cidades = [r[0] for r in query("SELECT DISTINCT cidade FROM clientes WHERE cidade IS NOT NULL "
                                   "AND cidade <> '' ORDER BY cidade")]
    return render_template("clientes/lista.html", clientes=clientes, total=total, cidades=cidades,
                           q=q, status=status, cidade=cidade)


@bp.route("/novo", methods=["GET", "POST"])
@perfil("admin", "atendente")
def novo():
    dados, erros = {"status": "ativo"}, {}
    if request.method == "POST":
        dados, erros = validar(request.form)
        if not erros:
            db = get_db()
            with db:
                cur = db.execute(
                    f"INSERT INTO clientes ({', '.join(CAMPOS)}, criado_por) "
                    f"VALUES ({', '.join('?' * len(CAMPOS))}, ?)",
                    [dados[k] or None for k in CAMPOS] + [g.user["id"]])
            flash(f"Cliente \"{dados['nome']}\" cadastrado.", "ok")
            destino = request.args.get("voltar")
            if destino == "orcamento":
                return redirect(url_for("orcamentos.novo", cliente=cur.lastrowid))
            return redirect(url_for("clientes.detalhe", cliente_id=cur.lastrowid))
        flash("Corrija os campos destacados para salvar o cliente.", "erro")
    return render_template("clientes/form.html", c=dados, erros=erros, novo=True,
                           exemplo=json.dumps(EXEMPLO, ensure_ascii=False))


@bp.route("/<int:cliente_id>/editar", methods=["GET", "POST"])
@perfil("admin", "atendente")
def editar(cliente_id):
    c = dict(get_cliente(cliente_id))
    c["documento"] = fmt_documento(c["documento"])
    erros = {}
    if request.method == "POST":
        dados, erros = validar(request.form, cliente_id)
        if not erros:
            db = get_db()
            with db:
                db.execute(
                    f"UPDATE clientes SET {', '.join(k + ' = ?' for k in CAMPOS)}, "
                    "atualizado_em = ?, atualizado_por = ? WHERE id = ?",
                    [dados[k] or None for k in CAMPOS] + [agora_iso(), g.user["id"], cliente_id])
            flash("Dados do cliente atualizados.", "ok")
            return redirect(url_for("clientes.detalhe", cliente_id=cliente_id))
        c = {**dados, "id": cliente_id, "documento": request.form.get("documento", "")}
        flash("Corrija os campos destacados para salvar o cliente.", "erro")
    return render_template("clientes/form.html", c=c, erros=erros, novo=False, exemplo=None)


@bp.route("/<int:cliente_id>")
def detalhe(cliente_id):
    c = get_cliente(cliente_id)
    aba = request.args.get("aba", "visao")
    orcs = query(f"SELECT o.*, {SQL_TOTAL_ORC} AS total FROM orcamentos o WHERE o.cliente_id = ? "
                 "ORDER BY o.seq DESC", (cliente_id,))
    oss = query(f"SELECT os.*, {SQL_TOTAL_OS} AS total, u.nome AS responsavel FROM ordens_servico os "
                "LEFT JOIN usuarios u ON u.id = os.responsavel_id WHERE os.cliente_id = ? "
                "ORDER BY os.seq DESC", (cliente_id,))
    contas = query("SELECT * FROM contas WHERE cliente_id = ? ORDER BY vencimento DESC", (cliente_id,))
    equipamentos = query("SELECT * FROM equipamentos WHERE cliente_id = ? ORDER BY tipo, marca_modelo",
                         (cliente_id,))
    stats = {
        "orcamentos": len(orcs),
        "os_abertas": sum(1 for o in oss if o["status"] != "concluida"),
        "recebido": sum(x["valor"] for x in contas if x["pago_em"]),
        "aberto": sum(x["valor"] for x in contas if not x["pago_em"]),
    }
    return render_template("clientes/detalhe.html", c=c, aba=aba, orcs=orcs, oss=oss,
                           contas=contas, equipamentos=equipamentos, stats=stats,
                           timeline=linha_do_tempo(c, oss))


def linha_do_tempo(c, oss):
    """RF-09: histórico de relacionamento com orçamentos, OS e financeiro."""
    eventos = []
    verbos = {"rascunho": "criado", "enviado": "enviado ao cliente", "aprovado": "aprovado",
              "recusado": "recusado", "os": "convertido em OS", "faturado": "faturado"}
    cores = {"rascunho": "amber", "enviado": "amber", "aprovado": "green", "recusado": "red",
             "os": "blue", "faturado": "green"}
    for h in query(f"SELECT h.*, o.seq, o.descricao, {SQL_TOTAL_ORC} AS total FROM orcamento_historico h "
                   "JOIN orcamentos o ON o.id = h.orcamento_id WHERE o.cliente_id = ?", (c["id"],)):
        eventos.append((h["data"], f"Orçamento {codigo('ORC', h['seq'])} {verbos.get(h['status'], h['status'])}",
                        f"{h['descricao']} · {moeda(h['total'])}", cores.get(h["status"], "gray"),
                        url_for("orcamentos.detalhe", orc_id=h["orcamento_id"])))
    nomes_os = {"aberta": ("aberta", "purple"), "andamento": ("em andamento", "blue"),
                "aguardando": ("aguardando", "amber"), "concluida": ("concluída", "green")}
    os_map = {o["id"]: o for o in oss}
    for h in query("SELECT h.* FROM os_historico h JOIN ordens_servico os ON os.id = h.os_id "
                   "WHERE os.cliente_id = ? AND h.status IN ('aberta', 'concluida')", (c["id"],)):
        o = os_map[h["os_id"]]
        nome, cor = nomes_os[h["status"]]
        sub = f"{o['titulo']} · {o['responsavel'] or 'sem responsável'}" if h["status"] == "aberta" \
            else moeda(o["total"])
        eventos.append((h["data"], f"OS {codigo('OS', o['seq'])} {nome}", sub, cor,
                        url_for("ordens.detalhe", os_id=o["id"])))
    for x in query("SELECT * FROM contas WHERE cliente_id = ? AND pago_em IS NOT NULL", (c["id"],)):
        eventos.append((x["pago_em"] + " 23:59", "Pagamento recebido",
                        f"{x['descricao']} · {moeda(x['valor'])}", "green", None))
    eventos.append((c["criado_em"], "Cliente cadastrado", "", "gray", None))
    eventos.sort(key=lambda e: e[0], reverse=True)
    return eventos[:15]


@bp.route("/<int:cliente_id>/status", methods=["POST"])
@perfil("admin", "atendente")
def alternar_status(cliente_id):
    c = get_cliente(cliente_id)
    novo = "inativo" if c["status"] == "ativo" else "ativo"
    db = get_db()
    with db:
        db.execute("UPDATE clientes SET status = ?, atualizado_em = ?, atualizado_por = ? WHERE id = ?",
                   (novo, agora_iso(), g.user["id"], cliente_id))
    flash(f"Cliente {'inativado' if novo == 'inativo' else 'reativado'}.", "ok")
    return redirect(url_for("clientes.detalhe", cliente_id=cliente_id))


def tem_movimentacao(cliente_id) -> bool:
    return bool(scalar(
        "SELECT (SELECT COUNT(*) FROM orcamentos WHERE cliente_id = ?) + "
        "(SELECT COUNT(*) FROM ordens_servico WHERE cliente_id = ?) + "
        "(SELECT COUNT(*) FROM contas WHERE cliente_id = ?)", (cliente_id,) * 3))


@bp.route("/<int:cliente_id>/excluir", methods=["POST"])
@perfil("admin")
def excluir(cliente_id):
    """RN-07: cliente com movimentação não é excluído, apenas inativado."""
    get_cliente(cliente_id)
    if tem_movimentacao(cliente_id):
        flash("Este cliente tem orçamentos, OS ou lançamentos e não pode ser excluído. "
              "Use \"Inativar\" para preservar o histórico.", "erro")
        return redirect(url_for("clientes.detalhe", cliente_id=cliente_id))
    db = get_db()
    with db:
        db.execute("DELETE FROM equipamentos WHERE cliente_id = ?", (cliente_id,))
        db.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    flash("Cliente excluído.", "ok")
    return redirect(url_for("clientes.lista"))


@bp.route("/<int:cliente_id>/anonimizar", methods=["POST"])
@perfil("admin")
def anonimizar(cliente_id):
    """RNF-12 (LGPD): remove dados pessoais mantendo o histórico contábil."""
    c = get_cliente(cliente_id)
    if c["status"] != "inativo":
        flash("Inative o cliente antes de anonimizar os dados.", "erro")
        return redirect(url_for("clientes.detalhe", cliente_id=cliente_id))
    db = get_db()
    with db:
        db.execute("UPDATE clientes SET nome = ?, documento = NULL, contato = NULL, email = NULL, "
                   "telefone = NULL, cep = NULL, endereco = NULL, numero = NULL, complemento = NULL, "
                   "anotacoes = NULL, atualizado_em = ?, atualizado_por = ? WHERE id = ?",
                   (f"Cliente anonimizado #{cliente_id}", agora_iso(), g.user["id"], cliente_id))
    flash("Dados pessoais anonimizados. O histórico de orçamentos, OS e contas foi mantido.", "ok")
    return redirect(url_for("clientes.detalhe", cliente_id=cliente_id))


@bp.route("/<int:cliente_id>/equipamentos", methods=["POST"])
def novo_equipamento(cliente_id):
    get_cliente(cliente_id)
    tipo = request.form.get("tipo", "").strip()
    if not tipo:
        flash("Informe o tipo do equipamento (ex.: Notebook).", "erro")
    else:
        db = get_db()
        with db:
            db.execute("INSERT INTO equipamentos (cliente_id, tipo, marca_modelo, numero_serie) "
                       "VALUES (?, ?, ?, ?)",
                       (cliente_id, tipo, request.form.get("marca_modelo", "").strip() or None,
                        request.form.get("numero_serie", "").strip() or None))
        flash("Equipamento adicionado.", "ok")
    return redirect(url_for("clientes.detalhe", cliente_id=cliente_id, aba="equipamentos"))
