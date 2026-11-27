"""Relatórios gerenciais e exportações (RF-43)."""
import csv
import io
from datetime import date

from flask import Blueprint, Response, render_template

from ..auth import perfil
from ..db import query
from ..regras import SQL_TOTAL_OS
from ..util import MESES, STATUS_ESTOQUE, STATUS_OS, codigo, data_br, hoje, hoje_iso, status_estoque

bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")


@bp.before_request
@perfil("admin")
def _somente_admin():
    return None


def ultimos_meses(n=6):
    h = hoje()
    meses = []
    for i in range(n - 1, -1, -1):
        ano, mes = h.year, h.month - i
        while mes <= 0:
            mes += 12
            ano -= 1
        meses.append(date(ano, mes, 1).isoformat()[:7])
    return meses


@bp.route("/")
def index():
    linhas = []
    for m in ultimos_meses():
        r = query(
            "SELECT "
            "(SELECT COALESCE(SUM(valor),0) FROM contas WHERE tipo='receber' AND substr(pago_em,1,7)=?) AS recebido, "
            "(SELECT COALESCE(SUM(valor),0) FROM contas WHERE tipo='pagar' AND substr(pago_em,1,7)=?) AS pago, "
            "(SELECT COUNT(*) FROM ordens_servico WHERE substr(conclusao,1,7)=?) AS os_concluidas, "
            "(SELECT COUNT(*) FROM orcamentos WHERE substr(criado_em,1,7)=?) AS orcamentos",
            (m, m, m, m), one=True)
        linhas.append({"mes": f"{MESES[int(m[5:]) - 1][:3]}/{m[:4]}", **dict(r),
                       "saldo": r["recebido"] - r["pago"]})
    maior = max([max(l["recebido"], l["pago"]) for l in linhas] + [1])
    top_servicos = query(
        "SELECT descricao, SUM(quantidade) AS qtd, SUM(quantidade * valor_unitario) AS valor "
        "FROM os_itens WHERE tipo <> 'peca' GROUP BY descricao ORDER BY valor DESC LIMIT 6")
    top_pecas = query(
        "SELECT descricao, SUM(quantidade) AS qtd, SUM(quantidade * valor_unitario) AS valor "
        "FROM os_itens WHERE tipo = 'peca' GROUP BY descricao ORDER BY qtd DESC LIMIT 6")
    conversao = query(
        "SELECT COUNT(*) AS total, SUM(status IN ('aprovado','os','faturado')) AS aprovados, "
        "SUM(status = 'recusado') AS recusados FROM orcamentos WHERE status <> 'rascunho'", one=True)
    por_tecnico = query(
        f"SELECT u.nome, COUNT(os.id) AS n, SUM(os.status='concluida') AS concluidas, "
        f"COALESCE(SUM(CASE WHEN os.status='concluida' THEN {SQL_TOTAL_OS} END), 0) AS valor "
        "FROM usuarios u LEFT JOIN ordens_servico os ON os.responsavel_id = u.id "
        "WHERE u.perfil IN ('tecnico','admin') GROUP BY u.id ORDER BY n DESC")
    return render_template("relatorios.html", linhas=linhas, maior=maior, top_servicos=top_servicos,
                           top_pecas=top_pecas, conversao=conversao, por_tecnico=por_tecnico)


def csv_response(nome, cabecalho, linhas):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(cabecalho)
    w.writerows(linhas)
    return Response("﻿" + buf.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={nome}-{hoje_iso()}.csv"})


def br(v):
    return f"{v:.2f}".replace(".", ",")


@bp.route("/estoque.csv")
def estoque_csv():
    itens = query("SELECT * FROM itens_estoque ORDER BY categoria, descricao")
    return csv_response("estoque", ["SKU", "Descrição", "Categoria", "Quantidade", "Mínimo",
                                    "Preço", "Valor em estoque", "Situação", "Fornecedor"],
                        [[i["sku"], i["descricao"], i["categoria"], i["quantidade"],
                          i["estoque_minimo"], br(i["preco"]), br(i["quantidade"] * i["preco"]),
                          STATUS_ESTOQUE[status_estoque(i["quantidade"], i["estoque_minimo"])][0],
                          i["fornecedor"] or ""] for i in itens])


@bp.route("/os.csv")
def os_csv():
    oss = query(f"SELECT os.*, c.nome AS cliente, u.nome AS responsavel, {SQL_TOTAL_OS} AS total "
                "FROM ordens_servico os JOIN clientes c ON c.id = os.cliente_id "
                "LEFT JOIN usuarios u ON u.id = os.responsavel_id ORDER BY os.seq")
    return csv_response("ordens-de-servico",
                        ["OS", "Serviço", "Cliente", "Responsável", "Situação", "Abertura",
                         "Previsão", "Conclusão", "Total"],
                        [[codigo("OS", o["seq"]), o["titulo"], o["cliente"], o["responsavel"] or "",
                          STATUS_OS[o["status"]][0], data_br(o["abertura"]),
                          data_br(o["previsao"]) if o["previsao"] else "",
                          data_br(o["conclusao"]) if o["conclusao"] else "", br(o["total"])]
                         for o in oss])
