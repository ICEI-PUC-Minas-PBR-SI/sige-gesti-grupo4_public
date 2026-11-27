"""Regras de negócio que cruzam módulos.

As funções daqui não fazem commit: quem chama envolve a operação em `with db:`,
para que tudo seja gravado ou nada seja (RNF-14).
"""
from .util import agora_iso, codigo, hoje_iso, mais_dias


# Expressões SQL reutilizadas nas listagens (alias o = orcamentos, os = ordens_servico)
SQL_TOTAL_ORC = ("((SELECT COALESCE(SUM(quantidade * valor_unitario), 0) FROM orcamento_itens "
                 "WHERE orcamento_id = o.id) - o.desconto)")
SQL_TOTAL_OS = ("((SELECT COALESCE(SUM(quantidade * valor_unitario), 0) FROM os_itens "
                "WHERE os_id = os.id) - os.desconto)")


class RegraError(Exception):
    """Violação de regra de negócio, com mensagem pronta para o usuário (RNF-04)."""


# ------------------------------------------------------------------ geral

def proximo_seq(db, tabela: str, where: str = "", params=()) -> int:
    sql = f"SELECT COALESCE(MAX(seq), 0) + 1 FROM {tabela}"
    if where:
        sql += f" WHERE {where}"
    return db.execute(sql, params).fetchone()[0]


def calcular_totais(itens, desconto: float):
    """RN-03: total = serviços + peças − desconto; desconto não pode exceder o subtotal."""
    subtotal = round(sum(float(i["quantidade"]) * float(i["valor_unitario"]) for i in itens), 2)
    desconto = round(float(desconto or 0), 2)
    if desconto < 0:
        raise RegraError("O desconto não pode ser negativo.")
    if desconto > subtotal:
        raise RegraError("O desconto não pode ser maior que o subtotal "
                         f"(R$ {subtotal:.2f}).".replace(".", ","))
    return subtotal, round(subtotal - desconto, 2)


# ------------------------------------------------------------------ estoque

def movimentar_estoque(db, item_id: int, tipo: str, quantidade: int, referencia: str,
                       usuario_id: int, os_id: int | None = None) -> int:
    """Lança uma movimentação com sinal e devolve o novo saldo (RF-30, RF-31, RN-04)."""
    item = db.execute("SELECT * FROM itens_estoque WHERE id = ?", (item_id,)).fetchone()
    if item is None:
        raise RegraError("Item de estoque não encontrado.")
    if quantidade == 0:
        raise RegraError("Informe uma quantidade diferente de zero.")
    saldo = item["quantidade"] + quantidade
    if saldo < 0:
        raise RegraError(f"Saldo insuficiente de \"{item['descricao']}\": há "
                         f"{item['quantidade']} un. e a operação pede {-quantidade}.")
    db.execute("UPDATE itens_estoque SET quantidade = ?, atualizado_em = ?, atualizado_por = ? "
               "WHERE id = ?", (saldo, agora_iso(), usuario_id, item_id))
    db.execute("INSERT INTO movimentacoes_estoque (item_id, tipo, quantidade, saldo, referencia, "
               "os_id, usuario_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
               (item_id, tipo, quantidade, saldo, referencia, os_id, usuario_id))
    return saldo


def gerar_sku(db, descricao: str) -> str:
    palavras = [p for p in "".join(c if c.isalnum() else " " for c in descricao.upper()).split()]
    base = "-".join(p[:3] for p in palavras[:3]) or "ITEM"
    sku, n = base, 2
    while db.execute("SELECT 1 FROM itens_estoque WHERE sku = ?", (sku,)).fetchone():
        sku = f"{base}-{n}"
        n += 1
    return sku


# ------------------------------------------------------------------ orçamentos

TRANSICOES_ORCAMENTO = {
    "rascunho": {"enviado"},
    "enviado": {"aprovado", "recusado", "rascunho"},
    "recusado": {"rascunho"},
    "aprovado": {"enviado"},
}


def registrar_historico_orcamento(db, orc_id, status, usuario_id):
    db.execute("INSERT INTO orcamento_historico (orcamento_id, status, usuario_id) VALUES (?, ?, ?)",
               (orc_id, status, usuario_id))


def mudar_status_orcamento(db, orc_id: int, novo: str, usuario_id: int):
    orc = db.execute("SELECT * FROM orcamentos WHERE id = ?", (orc_id,)).fetchone()
    if orc is None:
        raise RegraError("Orçamento não encontrado.")
    if novo not in TRANSICOES_ORCAMENTO.get(orc["status"], set()):
        raise RegraError("Essa mudança de situação não é permitida para este orçamento.")
    if novo == "aprovado" and orc["validade"] < hoje_iso():
        raise RegraError("O orçamento está expirado. Volte para rascunho e atualize a validade.")
    db.execute("UPDATE orcamentos SET status = ?, atualizado_em = ?, atualizado_por = ? WHERE id = ?",
               (novo, agora_iso(), usuario_id, orc_id))
    registrar_historico_orcamento(db, orc_id, novo, usuario_id)


def salvar_itens_orcamento(db, orc_id: int, itens):
    db.execute("DELETE FROM orcamento_itens WHERE orcamento_id = ?", (orc_id,))
    for i in itens:
        db.execute("INSERT INTO orcamento_itens (orcamento_id, tipo, item_estoque_id, descricao, "
                   "quantidade, valor_unitario) VALUES (?, ?, ?, ?, ?, ?)",
                   (orc_id, i["tipo"], i.get("item_estoque_id"), i["descricao"],
                    i["quantidade"], i["valor_unitario"]))


def converter_orcamento_em_os(db, orc_id: int, usuario_id: int, responsavel_id=None,
                              previsao=None) -> int:
    """RF-17 / RN-02: copia cliente, equipamento, serviços e peças para uma nova OS."""
    orc = db.execute("SELECT * FROM orcamentos WHERE id = ?", (orc_id,)).fetchone()
    if orc is None:
        raise RegraError("Orçamento não encontrado.")
    if orc["status"] != "aprovado":
        raise RegraError("Somente orçamentos aprovados podem gerar ordem de serviço.")
    equip = None
    if orc["equipamento_id"]:
        equip = db.execute("SELECT * FROM equipamentos WHERE id = ?",
                           (orc["equipamento_id"],)).fetchone()
    seq = proximo_seq(db, "ordens_servico")
    cur = db.execute(
        "INSERT INTO ordens_servico (seq, cliente_id, orcamento_id, equipamento_id, titulo, "
        "equip_tipo, equip_modelo, equip_serie, observacoes, responsavel_id, desconto, abertura, "
        "previsao, criado_por) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (seq, orc["cliente_id"], orc_id, orc["equipamento_id"], orc["descricao"],
         equip["tipo"] if equip else None, equip["marca_modelo"] if equip else None,
         equip["numero_serie"] if equip else None, orc["observacoes"], responsavel_id,
         orc["desconto"], hoje_iso(), previsao or mais_dias(5), usuario_id))
    os_id = cur.lastrowid
    db.execute("INSERT INTO os_historico (os_id, status, usuario_id) VALUES (?, 'aberta', ?)",
               (os_id, usuario_id))
    itens = db.execute("SELECT * FROM orcamento_itens WHERE orcamento_id = ?", (orc_id,)).fetchall()
    for i in itens:
        adicionar_item_os(db, os_id, i["tipo"], i["descricao"], i["quantidade"],
                          i["valor_unitario"], usuario_id, i["item_estoque_id"])
    db.execute("UPDATE orcamentos SET status = 'os', atualizado_em = ?, atualizado_por = ? "
               "WHERE id = ?", (agora_iso(), usuario_id, orc_id))
    registrar_historico_orcamento(db, orc_id, "os", usuario_id)
    return os_id


# ------------------------------------------------------------------ ordens de serviço

def adicionar_item_os(db, os_id: int, tipo: str, descricao: str, quantidade, valor_unitario,
                      usuario_id: int, item_estoque_id=None) -> int:
    """RF-24 / RF-25: peças lançadas dão baixa automática no estoque."""
    if float(quantidade) <= 0:
        raise RegraError("A quantidade deve ser maior que zero.")
    if tipo == "peca":
        if not item_estoque_id:
            raise RegraError("Selecione a peça do estoque.")
        if float(quantidade) != int(float(quantidade)):
            raise RegraError("Peças do estoque usam quantidade inteira.")
        os_row = db.execute("SELECT seq FROM ordens_servico WHERE id = ?", (os_id,)).fetchone()
        movimentar_estoque(db, item_estoque_id, "saida", -int(float(quantidade)),
                           codigo("OS", os_row["seq"]), usuario_id, os_id)
    cur = db.execute("INSERT INTO os_itens (os_id, tipo, item_estoque_id, descricao, quantidade, "
                     "valor_unitario) VALUES (?, ?, ?, ?, ?, ?)",
                     (os_id, tipo, item_estoque_id, descricao, quantidade, valor_unitario))
    tocar_os(db, os_id, usuario_id)
    return cur.lastrowid


def remover_item_os(db, os_item_id: int, usuario_id: int):
    """RF-25: peça removida volta ao estoque."""
    item = db.execute("SELECT oi.*, os.seq FROM os_itens oi JOIN ordens_servico os "
                      "ON os.id = oi.os_id WHERE oi.id = ?", (os_item_id,)).fetchone()
    if item is None:
        raise RegraError("Item não encontrado.")
    if item["tipo"] == "peca" and item["item_estoque_id"]:
        movimentar_estoque(db, item["item_estoque_id"], "entrada", int(item["quantidade"]),
                           f"Devolução {codigo('OS', item['seq'])}", usuario_id, item["os_id"])
    db.execute("DELETE FROM os_itens WHERE id = ?", (os_item_id,))
    tocar_os(db, item["os_id"], usuario_id)
    return item["os_id"]


def tocar_os(db, os_id, usuario_id):
    db.execute("UPDATE ordens_servico SET atualizado_em = ?, atualizado_por = ? WHERE id = ?",
               (agora_iso(), usuario_id, os_id))


def totais_os(db, os_id: int):
    itens = db.execute("SELECT * FROM os_itens WHERE os_id = ?", (os_id,)).fetchall()
    os_row = db.execute("SELECT desconto FROM ordens_servico WHERE id = ?", (os_id,)).fetchone()
    servicos = sum(i["quantidade"] * i["valor_unitario"] for i in itens if i["tipo"] != "peca")
    pecas = sum(i["quantidade"] * i["valor_unitario"] for i in itens if i["tipo"] == "peca")
    desconto = min(os_row["desconto"], servicos + pecas)
    return {"servicos": round(servicos, 2), "pecas": round(pecas, 2), "desconto": desconto,
            "total": round(servicos + pecas - desconto, 2)}


def os_editavel(os_row, perfil: str) -> bool:
    """RN-09: OS concluída só pode ser alterada pelo administrador."""
    return os_row["status"] != "concluida" or perfil == "admin"


def mudar_status_os(db, os_id: int, novo: str, usuario_id: int, perfil: str):
    os_row = db.execute("SELECT * FROM ordens_servico WHERE id = ?", (os_id,)).fetchone()
    if os_row is None:
        raise RegraError("Ordem de serviço não encontrada.")
    if novo not in ("aberta", "andamento", "aguardando"):
        raise RegraError("Para concluir, use \"Finalizar ordem de serviço\".")
    if os_row["status"] == novo:
        return
    if not os_editavel(os_row, perfil):
        raise RegraError("Somente o administrador pode reabrir uma OS concluída.")
    db.execute("UPDATE ordens_servico SET status = ?, conclusao = NULL, atualizado_em = ?, "
               "atualizado_por = ? WHERE id = ?", (novo, agora_iso(), usuario_id, os_id))
    db.execute("INSERT INTO os_historico (os_id, status, usuario_id) VALUES (?, ?, ?)",
               (os_id, novo, usuario_id))


def concluir_os(db, os_id: int, usuario_id: int, forma_pagamento: str, vencimento: str):
    """RF-26 / RN-06: conclui a OS e gera (uma única) conta a receber."""
    os_row = db.execute("SELECT * FROM ordens_servico WHERE id = ?", (os_id,)).fetchone()
    if os_row is None:
        raise RegraError("Ordem de serviço não encontrada.")
    if os_row["status"] == "concluida":
        raise RegraError("Esta ordem de serviço já está concluída.")
    if not vencimento:
        raise RegraError("Informe o vencimento da conta a receber.")
    total = totais_os(db, os_id)["total"]
    db.execute("UPDATE ordens_servico SET status = 'concluida', conclusao = ?, atualizado_em = ?, "
               "atualizado_por = ? WHERE id = ?", (hoje_iso(), agora_iso(), usuario_id, os_id))
    db.execute("INSERT INTO os_historico (os_id, status, usuario_id) VALUES (?, 'concluida', ?)",
               (os_id, usuario_id))

    conta = db.execute("SELECT * FROM contas WHERE os_id = ?", (os_id,)).fetchone()
    conta_id = None
    if conta is not None:
        conta_id = conta["id"]
        if not conta["pago_em"] and total > 0:
            db.execute("UPDATE contas SET valor = ?, vencimento = ?, forma_pagamento = ?, "
                       "atualizado_em = ?, atualizado_por = ? WHERE id = ?",
                       (total, vencimento, forma_pagamento, agora_iso(), usuario_id, conta_id))
    elif total > 0:
        seq = proximo_seq(db, "contas", "tipo = 'receber'")
        cur = db.execute(
            "INSERT INTO contas (tipo, seq, descricao, cliente_id, os_id, categoria, valor, "
            "vencimento, forma_pagamento, criado_por) VALUES ('receber', ?, ?, ?, ?, 'Serviços', "
            "?, ?, ?, ?)",
            (seq, f"{os_row['titulo']} — {codigo('OS', os_row['seq'])}", os_row["cliente_id"],
             os_id, total, vencimento, forma_pagamento, usuario_id))
        conta_id = cur.lastrowid

    if os_row["orcamento_id"]:
        orc = db.execute("SELECT status FROM orcamentos WHERE id = ?",
                         (os_row["orcamento_id"],)).fetchone()
        if orc and orc["status"] == "os":
            db.execute("UPDATE orcamentos SET status = 'faturado', atualizado_em = ?, "
                       "atualizado_por = ? WHERE id = ?",
                       (agora_iso(), usuario_id, os_row["orcamento_id"]))
            registrar_historico_orcamento(db, os_row["orcamento_id"], "faturado", usuario_id)
    return conta_id


# ------------------------------------------------------------------ financeiro

def marcar_conta_paga(db, conta_id: int, data_pagamento: str, forma: str, usuario_id: int):
    conta = db.execute("SELECT * FROM contas WHERE id = ?", (conta_id,)).fetchone()
    if conta is None:
        raise RegraError("Conta não encontrada.")
    if conta["pago_em"]:
        raise RegraError("Esta conta já foi marcada como paga.")
    if not data_pagamento:
        raise RegraError("Informe a data do pagamento.")
    if data_pagamento > hoje_iso():
        raise RegraError("A data do pagamento não pode estar no futuro.")
    if not forma:
        raise RegraError("Informe a forma de pagamento.")
    db.execute("UPDATE contas SET pago_em = ?, forma_pagamento = ?, atualizado_em = ?, "
               "atualizado_por = ? WHERE id = ?",
               (data_pagamento, forma, agora_iso(), usuario_id, conta_id))
