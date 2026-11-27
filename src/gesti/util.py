"""Formatação no padrão brasileiro (RNF-05), validações (RF-06) e rótulos de situação."""
import re
from datetime import date, datetime, timedelta

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
               "sexta-feira", "sábado", "domingo"]
UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
       "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
FORMAS_PAGAMENTO = ["Pix", "Boleto", "Cartão de crédito", "Cartão de débito", "Dinheiro",
                    "Transferência"]
CATEGORIAS_ESTOQUE = ["Armazenamento", "Energia", "Insumos", "Memória", "Periféricos",
                      "Redes", "Telas"]
CATEGORIAS_PAGAR = ["Fornecedores", "Aluguel", "Serviços", "Impostos", "Utilidades", "Outros"]

# (rótulo, cor do selo)
STATUS_ORCAMENTO = {
    "rascunho": ("Rascunho", "gray"),
    "enviado": ("Aguardando aprovação", "amber"),
    "aprovado": ("Aprovado", "green"),
    "recusado": ("Recusado", "red"),
    "expirado": ("Expirado", "gray"),
    "os": ("Ordem de serviço", "blue"),
    "faturado": ("Faturado", "green"),
}
STATUS_OS = {
    "aberta": ("Aberta", "purple"),
    "andamento": ("Em andamento", "blue"),
    "aguardando": ("Aguardando", "amber"),
    "concluida": ("Concluída", "green"),
}
STATUS_ESTOQUE = {
    "ok": ("Em estoque", "green"),
    "baixo": ("Estoque baixo", "amber"),
    "zerado": ("Sem estoque", "red"),
}
STATUS_CONTA = {
    "pendente": ("Pendente", "amber"),
    "atraso": ("Em atraso", "red"),
    "pago": ("Pago", "green"),
}
STATUS_CLIENTE = {"ativo": ("Ativo", "green"), "inativo": ("Inativo", "gray")}
PERFIS = {"admin": "Administrador", "tecnico": "Técnico", "atendente": "Atendente"}


def hoje() -> date:
    return date.today()


def hoje_iso() -> str:
    return hoje().isoformat()


def agora_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def mais_dias(dias: int, base: date | None = None) -> str:
    return ((base or hoje()) + timedelta(days=dias)).isoformat()


# ---------------------------------------------------------------- formatação

def moeda(valor) -> str:
    v = float(valor or 0)
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if v < 0 else ''}R$ {s}"


def numero_br(valor) -> str:
    v = float(valor or 0)
    if v == int(v):
        return str(int(v))
    return f"{v:.2f}".replace(".", ",")


def _to_date(valor):
    if not valor:
        return None
    if isinstance(valor, (date, datetime)):
        return valor if isinstance(valor, date) else valor.date()
    try:
        return datetime.fromisoformat(str(valor)[:19]).date()
    except ValueError:
        return None


def data_br(valor) -> str:
    d = _to_date(valor)
    return d.strftime("%d/%m/%Y") if d else "—"


def data_curta(valor) -> str:
    d = _to_date(valor)
    return f"{d.day} {MESES[d.month - 1][:3]}" if d else "—"


def data_extenso(d: date) -> str:
    return f"{DIAS_SEMANA[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def codigo(prefixo: str, seq) -> str:
    return f"{prefixo}-{int(seq):04d}"


def iniciais(nome: str) -> str:
    partes = [p for p in re.split(r"\s+", nome or "") if p and p[0].isalpha()
              and p.lower() not in {"de", "da", "do", "dos", "das", "e", "&"}]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][0].upper()
    return (partes[0][0] + partes[1][0]).upper()


def so_digitos(s) -> str:
    return re.sub(r"\D", "", s or "")


def fmt_documento(doc) -> str:
    d = so_digitos(doc)
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return doc or ""


def fmt_telefone(tel) -> str:
    d = so_digitos(tel)
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return tel or ""


def fmt_cep(cep) -> str:
    d = so_digitos(cep)
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else (cep or "")


def parse_valor(s) -> float | None:
    """Aceita '1.234,56', '1234,56' ou '1234.56'."""
    if s is None:
        return None
    s = str(s).strip().replace("R$", "").replace(" ", "")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def parse_int(s, padrao=None):
    try:
        return int(str(s).strip())
    except (TypeError, ValueError):
        return padrao


# ---------------------------------------------------------------- validação

def cpf_valido(cpf: str) -> bool:
    d = so_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        dv = (soma * 10) % 11 % 10
        if dv != int(d[n]):
            return False
    return True


def cnpj_valido(cnpj: str) -> bool:
    d = so_digitos(cnpj)
    if len(d) != 14 or d == d[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    for pesos, pos in ((pesos1, 12), (pesos2, 13)):
        soma = sum(int(d[i]) * pesos[i] for i in range(pos))
        resto = soma % 11
        dv = 0 if resto < 2 else 11 - resto
        if dv != int(d[pos]):
            return False
    return True


def documento_valido(doc: str) -> bool:
    d = so_digitos(doc)
    return cpf_valido(d) if len(d) == 11 else cnpj_valido(d) if len(d) == 14 else False


def email_valido(email: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or ""))


def telefone_valido(tel: str) -> bool:
    return len(so_digitos(tel)) in (10, 11)


def cep_valido(cep: str) -> bool:
    return len(so_digitos(cep)) == 8


# ---------------------------------------------------------------- situações calculadas

def status_estoque(qtd, minimo) -> str:
    """RN-05."""
    if qtd <= 0:
        return "zerado"
    if qtd <= minimo:
        return "baixo"
    return "ok"


def status_conta(conta) -> str:
    """RN-08."""
    if conta["pago_em"]:
        return "pago"
    if conta["vencimento"] < hoje_iso():
        return "atraso"
    return "pendente"


def status_orcamento(orc) -> str:
    """Orçamento enviado com validade vencida aparece como Expirado."""
    if orc["status"] == "enviado" and orc["validade"] < hoje_iso():
        return "expirado"
    return orc["status"]


def register_filters(app):
    app.jinja_env.filters.update(
        moeda=moeda, data=data_br, data_curta=data_curta, doc=fmt_documento,
        tel=fmt_telefone, cep=fmt_cep, iniciais=iniciais, num=numero_br,
    )
    app.jinja_env.globals.update(
        codigo=codigo, STATUS_ORCAMENTO=STATUS_ORCAMENTO, STATUS_OS=STATUS_OS,
        STATUS_ESTOQUE=STATUS_ESTOQUE, STATUS_CONTA=STATUS_CONTA,
        STATUS_CLIENTE=STATUS_CLIENTE, PERFIS=PERFIS, UFS=UFS,
        FORMAS_PAGAMENTO=FORMAS_PAGAMENTO, CATEGORIAS_ESTOQUE=CATEGORIAS_ESTOQUE,
        CATEGORIAS_PAGAR=CATEGORIAS_PAGAR, status_estoque=status_estoque,
        status_conta=status_conta, status_orcamento=status_orcamento,
        hoje_iso=hoje_iso,
    )
