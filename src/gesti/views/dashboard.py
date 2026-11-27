"""Dashboard (RF-40 a RF-42)."""
from flask import Blueprint, render_template

from ..db import query, scalar
from ..regras import SQL_TOTAL_ORC
from ..util import MESES, data_extenso, hoje, hoje_iso, status_estoque

bp = Blueprint("dashboard", __name__)


def resumo_financeiro():
    h = hoje_iso()
    inicio_mes = hoje().replace(day=1).isoformat()
    r = {
        "a_receber": scalar("SELECT COALESCE(SUM(valor),0) FROM contas WHERE tipo='receber' AND pago_em IS NULL"),
        "n_receber": scalar("SELECT COUNT(*) FROM contas WHERE tipo='receber' AND pago_em IS NULL"),
        "n_receber_atraso": scalar("SELECT COUNT(*) FROM contas WHERE tipo='receber' AND pago_em IS NULL AND vencimento < ?", (h,)),
        "a_pagar": scalar("SELECT COALESCE(SUM(valor),0) FROM contas WHERE tipo='pagar' AND pago_em IS NULL"),
        "n_pagar": scalar("SELECT COUNT(*) FROM contas WHERE tipo='pagar' AND pago_em IS NULL"),
        "n_pagar_atraso": scalar("SELECT COUNT(*) FROM contas WHERE tipo='pagar' AND pago_em IS NULL AND vencimento < ?", (h,)),
        "recebido_mes": scalar("SELECT COALESCE(SUM(valor),0) FROM contas WHERE tipo='receber' AND pago_em >= ?", (inicio_mes,)),
        "n_recebido_mes": scalar("SELECT COUNT(*) FROM contas WHERE tipo='receber' AND pago_em >= ?", (inicio_mes,)),
        "atraso_receber": scalar("SELECT COALESCE(SUM(valor),0) FROM contas WHERE tipo='receber' AND pago_em IS NULL AND vencimento < ?", (h,)),
        "mes": MESES[hoje().month - 1],
    }
    previsto = r["recebido_mes"] + r["a_receber"]
    r["pct"] = round(100 * r["recebido_mes"] / previsto) if previsto else 0
    return r


@bp.route("/")
def index():
    h = hoje_iso()
    kpi = {
        "os_abertas": scalar("SELECT COUNT(*) FROM ordens_servico WHERE status <> 'concluida'"),
        "os_andamento": scalar("SELECT COUNT(*) FROM ordens_servico WHERE status = 'andamento'"),
        "orc_aguardando": scalar("SELECT COUNT(*) FROM orcamentos WHERE status='enviado' AND validade >= ?", (h,)),
        "orc_valor": scalar(f"SELECT COALESCE(SUM({SQL_TOTAL_ORC}), 0) FROM orcamentos o "
                            "WHERE o.status = 'enviado' AND o.validade >= ?", (h,)),
        "estoque_baixo": scalar("SELECT COUNT(*) FROM itens_estoque WHERE quantidade <= estoque_minimo"),
        "sem_estoque": scalar("SELECT COUNT(*) FROM itens_estoque WHERE quantidade = 0"),
    }
    os_recentes = query(
        "SELECT os.*, c.nome AS cliente, u.nome AS responsavel FROM ordens_servico os "
        "JOIN clientes c ON c.id = os.cliente_id LEFT JOIN usuarios u ON u.id = os.responsavel_id "
        "ORDER BY os.seq DESC LIMIT 5")
    orc_recentes = query(
        f"SELECT o.*, c.nome AS cliente, {SQL_TOTAL_ORC} AS total FROM orcamentos o "
        "JOIN clientes c ON c.id = o.cliente_id ORDER BY o.seq DESC LIMIT 5")
    alertas = query("SELECT * FROM itens_estoque WHERE quantidade <= estoque_minimo "
                    "ORDER BY (quantidade = 0) DESC, quantidade * 1.0 / MAX(estoque_minimo, 1) LIMIT 6")
    return render_template("dashboard.html", kpi=kpi, os_recentes=os_recentes,
                           orc_recentes=orc_recentes, alertas=alertas, fin=resumo_financeiro(),
                           hoje_extenso=data_extenso(hoje()), status_estoque=status_estoque)
