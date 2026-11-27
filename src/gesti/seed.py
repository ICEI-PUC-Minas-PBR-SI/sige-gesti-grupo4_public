"""Dados de exemplo da NexaHertz, os mesmos do protótipo.

As datas são relativas ao dia em que o banco é criado, para o Dashboard sempre
mostrar uma operação "viva".
"""
from datetime import date, datetime, time, timedelta

from werkzeug.security import generate_password_hash

from .util import MESES, so_digitos

SENHA_PADRAO = "gesti123"


def _dv_cpf(base9: str) -> str:
    d = base9
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        d += str((soma * 10) % 11 % 10)
    return d


def _dv_cnpj(base12: str) -> str:
    d = base12
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for p in (pesos, [6] + pesos):
        resto = sum(int(d[i]) * p[i] for i in range(len(d))) % 11
        d += str(0 if resto < 2 else 11 - resto)
    return d


def seed_db(db):
    hoje = date.today()

    def D(dias: int) -> str:
        return (hoje + timedelta(days=dias)).isoformat()

    def DT(dias: int, hora: int = 10) -> str:
        return datetime.combine(hoje + timedelta(days=dias), time(hora, 0)).strftime(
            "%Y-%m-%d %H:%M:%S")

    mes = MESES[hoje.month - 1]

    # ---------------------------------------------------------------- usuários
    usuarios = [
        ("Rodrigo Nunes", "rodrigo@nexahertz.com.br", "admin"),
        ("Ana Ribeiro", "ana@nexahertz.com.br", "tecnico"),
        ("Carlos Mendes", "carlos@nexahertz.com.br", "tecnico"),
        ("Bruno Tavares", "bruno@nexahertz.com.br", "tecnico"),
        ("Juliana Prado", "juliana@nexahertz.com.br", "atendente"),
    ]
    hash_ = generate_password_hash(SENHA_PADRAO)
    for nome, email, perfil in usuarios:
        db.execute("INSERT INTO usuarios (nome, email, senha_hash, perfil, criado_em) "
                   "VALUES (?, ?, ?, ?, ?)", (nome, email, hash_, perfil, DT(-700)))
    ADM, ANA, CARLOS, BRUNO, JU = 1, 2, 3, 4, 5

    # ---------------------------------------------------------------- clientes
    clientes = [
        # nome, doc, contato, email, telefone, cep, endereço, nº, compl, cidade, uf, status, desde
        ("TechHouse Ltda.", _dv_cnpj("123456780001"), "João Almeida",
         "joao.almeida@techhouse.com.br", "11987654321", "01310100", "Av. Paulista", "1578",
         "Conj. 82", "São Paulo", "SP", "ativo", -620),
        ("Mariana Costa", _dv_cpf("348912556"), "Mariana Costa", "mariana.costa@email.com",
         "19998123340", "13015904", "Rua Barão de Jaguara", "1200", "Apto 54", "Campinas", "SP",
         "ativo", -300),
        ("Padaria Pão Dourado ME", _dv_cnpj("234567890001"), "Sérgio Nunes",
         "contato@paodourado.com.br", "1332224510", "11010150", "Rua XV de Novembro", "88", "",
         "Santos", "SP", "ativo", -410),
        ("Clínica Vida Plena", _dv_cnpj("345678900001"), "Dra. Patrícia Lopes",
         "adm@clinicavidaplena.com.br", "4130247788", "80420090", "Av. Batel", "1750",
         "Sala 304", "Curitiba", "PR", "ativo", -250),
        ("Rafael Souza", _dv_cpf("219334870"), "Rafael Souza", "rafael.souza@email.com",
         "11971235566", "04538132", "Rua Funchal", "418", "", "São Paulo", "SP", "ativo", -120),
        ("Moura & Lima Advogados", _dv_cnpj("456789010001"), "Eduardo Moura",
         "eduardo@mouralima.adv.br", "3132619040", "30140071", "Av. Afonso Pena", "1500",
         "10º andar", "Belo Horizonte", "MG", "ativo", -500),
        ("Construtora Horizonte S.A.", _dv_cnpj("567890120001"), "Fernanda Reis",
         "fernanda.reis@horizonte.com.br", "1134567000", "04711130", "Av. das Nações Unidas",
         "12901", "", "São Paulo", "SP", "inativo", -800),
        ("Luciana Ferreira", _dv_cpf("402118667"), "Luciana Ferreira", "luciana.f@email.com",
         "21996542210", "22041001", "Rua Barata Ribeiro", "370", "", "Rio de Janeiro", "RJ",
         "inativo", -150),
    ]
    for c in clientes:
        db.execute("INSERT INTO clientes (nome, documento, contato, email, telefone, cep, endereco, "
                   "numero, complemento, cidade, uf, status, criado_em, criado_por) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (*c[:12], DT(c[12]), ADM))
    TECH, MARIANA, PADARIA, CLINICA, RAFAEL, MOURA, CONSTRUTORA, LUCIANA = range(1, 9)

    equipamentos = [
        (MARIANA, "Notebook", "Dell Inspiron 15 3520", "7HK2QX3"),
        (TECH, "Notebook", "Lenovo ThinkPad E14 (6 un.)", "Lote comercial"),
        (TECH, "Notebook", "Dell Latitude 3420 (3 un.)", "Setor comercial"),
        (PADARIA, "Desktop", "Computador do caixa", "CX-01"),
        (CLINICA, "Rede", "Rede da recepção", ""),
        (RAFAEL, "Notebook", "Lenovo IdeaPad 3", "PF2KX91"),
        (MOURA, "Desktop", "Estação de trabalho Dell OptiPlex", "OPX-07"),
        (LUCIANA, "Notebook", "Samsung Book NP550", "R7QX12"),
    ]
    for e in equipamentos:
        db.execute("INSERT INTO equipamentos (cliente_id, tipo, marca_modelo, numero_serie) "
                   "VALUES (?, ?, ?, ?)", e)

    # ---------------------------------------------------------------- serviços
    servicos = [
        ("Troca de SSD (mão de obra)", 160), ("Formatação e instalação do Windows 11", 150),
        ("Diagnóstico técnico", 80), ("Limpeza interna e troca de pasta térmica", 120),
        ("Configuração de rede", 250), ("Backup e migração de dados", 160),
        ("Manutenção preventiva (por equipamento)", 120), ("Instalação de memória", 60),
        ("Troca de tela de notebook", 180), ("Configuração de impressora", 120),
        ("Visita técnica", 90),
    ]
    db.executemany("INSERT INTO servicos (descricao, preco) VALUES (?, ?)", servicos)

    # ---------------------------------------------------------------- estoque
    itens = [
        ("SSD-480-KA4", "SSD 480 GB Kingston A400", "Armazenamento", 5, 290.00,
         "Kingston Distribuidora"),
        ("RAM-D4-8G", "Memória RAM DDR4 8 GB 3200 MHz", "Memória", 6, 219.90, "Alfa Componentes"),
        ("FNT-500-80P", "Fonte ATX 500 W 80 Plus", "Energia", 3, 329.00, "Alfa Componentes"),
        ("PST-MX4-4G", "Pasta térmica Arctic MX-4 (4 g)", "Insumos", 10, 49.90, "InfoParts"),
        ("TEC-DL-I15", "Teclado notebook Dell Inspiron 15", "Periféricos", 3, 159.00, "InfoParts"),
        ("BAT-LN-IP3", "Bateria notebook Lenovo IdeaPad 3", "Energia", 3, 389.00, "InfoParts"),
        ("CAB-HDMI-2M", "Cabo HDMI 2.0 — 2 m", "Periféricos", 15, 34.90, "Alfa Componentes"),
        ("RTR-TPL-C6", "Roteador TP-Link Archer C6", "Redes", 4, 279.00, "Distribuidora Net"),
        ("TLA-156-30P", "Tela 15,6\" LED HD 30 pinos", "Telas", 2, 469.00, "InfoParts"),
        ("HDE-1TB-U3", "HD externo 1 TB USB 3.0", "Armazenamento", 2, 349.00,
         "Kingston Distribuidora"),
    ]
    for sku, desc, cat, minimo, preco, forn in itens:
        db.execute("INSERT INTO itens_estoque (sku, descricao, categoria, quantidade, estoque_minimo, "
                   "preco, fornecedor, criado_em, criado_por) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?)",
                   (sku, desc, cat, minimo, preco, forn, DT(-200), ADM))
    SSD, RAM, FONTE, PASTA, TECLADO, BATERIA, HDMI, ROTEADOR, TELA, HDE = range(1, 11)

    saldos = {i: 0 for i in range(1, 11)}

    def mov(item, tipo, qtd, ref, dias, os_id=None, user=ADM):
        saldos[item] += qtd
        db.execute("INSERT INTO movimentacoes_estoque (item_id, tipo, quantidade, saldo, referencia, "
                   "os_id, data, usuario_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (item, tipo, qtd, saldos[item], ref, os_id, DT(dias, 9), user))

    mov(SSD, "entrada", 13, "NF 4532 · Kingston Distribuidora", -30)
    mov(RAM, "entrada", 8, "NF 4545 · Alfa Componentes", -40)
    mov(RAM, "saida", -5, "Venda balcão · Moura & Lima Advogados", -11)
    mov(FONTE, "entrada", 3, "NF 4380 · Alfa Componentes", -90)
    mov(FONTE, "saida", -3, "Venda balcão", -25)
    mov(PASTA, "entrada", 32, "NF 4410 · InfoParts", -60)
    mov(TECLADO, "entrada", 2, "NF 4410 · InfoParts", -60)
    mov(BATERIA, "entrada", 4, "NF 4410 · InfoParts", -60)
    mov(HDMI, "entrada", 40, "NF 4390 · Alfa Componentes", -80)
    mov(ROTEADOR, "entrada", 7, "NF 2210 · Distribuidora Net", -45)
    mov(TELA, "entrada", 1, "NF 4410 · InfoParts", -60)
    mov(HDE, "entrada", 2, "NF 4300 · Kingston Distribuidora", -100)
    mov(HDE, "saida", -2, "Venda balcão", -35)

    # ---------------------------------------------------------------- orçamentos
    # seq, cliente, equip, descrição, status, criado(d), validade(d), obs, itens, histórico
    S, P, A = "servico", "peca", "avulso"
    orcamentos = [
        (142, TECH, 2, "Manutenção preventiva — 6 notebooks", "faturado", -16, -1, "",
         [(S, None, "Manutenção preventiva (por equipamento)", 6, 120),
          (P, PASTA, "Pasta térmica Arctic MX-4 (4 g)", 6, 49.90)],
         [("rascunho", -16), ("enviado", -16), ("aprovado", -14), ("os", -12), ("faturado", -8)]),
        (143, LUCIANA, 8, "Troca de tela de notebook", "enviado", -35, -20, "",
         [(S, None, "Troca de tela de notebook", 1, 180),
          (P, TELA, "Tela 15,6\" LED HD 30 pinos", 1, 469)],
         [("rascunho", -35), ("enviado", -35)]),
        (144, MOURA, 7, "Upgrade de memória — 4 estações", "recusado", -14, 1, "",
         [(P, RAM, "Memória RAM DDR4 8 GB 3200 MHz", 4, 219.90),
          (S, None, "Instalação de memória", 4, 67.50)],
         [("rascunho", -14), ("enviado", -14), ("recusado", -9)]),
        (145, PADARIA, 4, "Formatação de 2 computadores do caixa", "rascunho", -8, 7, "",
         [(S, None, "Formatação e instalação do Windows 11", 2, 150)],
         [("rascunho", -8)]),
        (146, MARIANA, 1, "Troca de SSD 480 GB", "os", -7, 8, "",
         [(S, None, "Troca de SSD 480 GB (mão de obra)", 1, 160),
          (P, SSD, "SSD 480 GB Kingston A400", 1, 290)],
         [("rascunho", -7), ("enviado", -7), ("aprovado", -4), ("os", -3)]),
        (147, CLINICA, 5, "Configuração de rede da recepção", "os", -5, 10, "",
         [(S, None, "Configuração de rede", 1, 250),
          (P, ROTEADOR, "Roteador TP-Link Archer C6", 1, 279)],
         [("rascunho", -5), ("enviado", -5), ("aprovado", -2), ("os", -1)]),
        (148, TECH, 3, "Troca de SSD 480 GB em 3 notebooks", "enviado", -2, 13,
         "Notebooks do setor comercial. Clonagem do sistema incluída.",
         [(S, None, "Troca de SSD 480 GB (mão de obra)", 3, 160),
          (P, SSD, "SSD 480 GB Kingston A400", 3, 290)],
         [("rascunho", -2), ("enviado", -2)]),
    ]
    orc_ids = {}
    for seq, cli, eq, desc, st, criado, val, obs, its, hist in orcamentos:
        cur = db.execute(
            "INSERT INTO orcamentos (seq, cliente_id, equipamento_id, descricao, status, desconto, "
            "validade, condicoes, observacoes, criado_em, criado_por) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)",
            (seq, cli, eq, desc, st, D(val), "Execução em até 5 dias úteis. Garantia de 90 dias.",
             obs, DT(criado), JU))
        oid = cur.lastrowid
        orc_ids[seq] = oid
        for tipo, item, d, q, v in its:
            db.execute("INSERT INTO orcamento_itens (orcamento_id, tipo, item_estoque_id, descricao, "
                       "quantidade, valor_unitario) VALUES (?, ?, ?, ?, ?, ?)",
                       (oid, tipo, item, d, q, v))
        for h, dias in hist:
            db.execute("INSERT INTO orcamento_historico (orcamento_id, status, data, usuario_id) "
                       "VALUES (?, ?, ?, ?)", (oid, h, DT(dias, 11), JU))

    # ---------------------------------------------------------------- ordens de serviço
    # seq, cliente, orc, equip_id, título, tipo, modelo, série, acessórios, problema, laudo,
    # resp, status, abertura, previsão, conclusão, itens, histórico
    ordens = [
        (229, CLINICA, None, None, "Limpeza interna e troca de pasta térmica", "Desktop",
         "Computador da recepção", "", "", "Computador desligando sozinho após algumas horas.",
         "Superaquecimento. Limpeza interna e troca da pasta térmica realizadas.", ANA,
         "concluida", -24, -21, -21,
         [(S, None, "Limpeza interna e troca de pasta térmica", 1, 120),
          (P, PASTA, "Pasta térmica Arctic MX-4 (4 g)", 1, 49.90)],
         [("aberta", -24), ("andamento", -23), ("concluida", -21)]),
        (230, TECH, None, None, "Backup e migração de dados", "Servidor",
         "Servidor de arquivos", "", "HD externo do cliente",
         "Migrar arquivos do servidor antigo para o novo armazenamento.", "", CARLOS,
         "aberta", -1, 1, None, [(S, None, "Backup e migração de dados", 1, 160)],
         [("aberta", -1)]),
        (231, MOURA, None, 7, "Formatação e instalação do Windows 11", "Desktop",
         "Estação de trabalho Dell OptiPlex", "OPX-07", "",
         "Sistema lento e com erros de atualização.", "Backup concluído, instalação em curso.",
         BRUNO, "andamento", -2, 0, None,
         [(S, None, "Formatação e instalação do Windows 11", 1, 150)],
         [("aberta", -2), ("andamento", -1)]),
        (232, PADARIA, None, 4, "Diagnóstico técnico — computador do caixa", "Desktop",
         "Computador do caixa", "CX-01", "", "Computador não liga.",
         "Fonte com defeito. Cliente optou por trazer fonte própria.", ANA, "concluida",
         -17, -15, -15, [(S, None, "Diagnóstico técnico", 1, 80)],
         [("aberta", -17), ("concluida", -15)]),
        (233, TECH, 142, 2, "Manutenção preventiva — 6 notebooks", "Notebook",
         "Lenovo ThinkPad E14 (6 un.)", "Lote comercial", "Carregadores",
         "Manutenção preventiva semestral.",
         "Limpeza, troca de pasta térmica e atualização de drivers nos 6 equipamentos.", CARLOS,
         "concluida", -12, -8, -8,
         [(S, None, "Manutenção preventiva (por equipamento)", 6, 120),
          (P, PASTA, "Pasta térmica Arctic MX-4 (4 g)", 6, 49.90)],
         [("aberta", -12), ("andamento", -11), ("concluida", -8)]),
        (234, RAFAEL, None, 6, "Manutenção de notebook", "Notebook", "Lenovo IdeaPad 3",
         "PF2KX91", "Carregador", "Teclado com teclas falhando e bateria durando pouco.",
         "Aguardando aprovação do cliente para troca da bateria.", CARLOS, "aguardando",
         -3, 2, None, [(A, None, "Manutenção de notebook", 1, 180)],
         [("aberta", -3), ("andamento", -2), ("aguardando", -1)]),
        (235, MARIANA, 146, 1, "Troca de SSD 480 GB", "Notebook", "Dell Inspiron 15 3520",
         "7HK2QX3", "Carregador",
         "Notebook muito lento para iniciar e abrir programas. Travamentos frequentes.",
         "Diagnóstico concluído: HD com setores defeituosos. Clonagem em andamento.", ANA,
         "andamento", -3, 1, None,
         [(S, None, "Troca de SSD 480 GB (mão de obra)", 1, 160),
          (P, SSD, "SSD 480 GB Kingston A400", 1, 290)],
         [("aberta", -3), ("andamento", -2)]),
        (236, CLINICA, 147, 5, "Configuração de rede da recepção", "Rede", "Rede da recepção",
         "", "", "Wi-Fi instável na recepção e sem cobertura nos consultórios.", "", BRUNO,
         "aberta", -1, 2, None,
         [(S, None, "Configuração de rede", 1, 250),
          (P, ROTEADOR, "Roteador TP-Link Archer C6", 1, 279)],
         [("aberta", -1)]),
    ]
    os_ids = {}
    for (seq, cli, orc, eq, tit, tipo, modelo, serie, aces, prob, laudo, resp, st, ab, prev,
         concl, its, hist) in ordens:
        cur = db.execute(
            "INSERT INTO ordens_servico (seq, cliente_id, orcamento_id, equipamento_id, titulo, "
            "equip_tipo, equip_modelo, equip_serie, equip_acessorios, problema, laudo, "
            "responsavel_id, status, abertura, previsao, conclusao, criado_em, criado_por) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (seq, cli, orc_ids.get(orc), eq, tit, tipo, modelo, serie, aces, prob, laudo, resp,
             st, D(ab), D(prev), D(concl) if concl is not None else None, DT(ab), resp))
        oid = cur.lastrowid
        os_ids[seq] = oid
        for t, item, d, q, v in its:
            db.execute("INSERT INTO os_itens (os_id, tipo, item_estoque_id, descricao, quantidade, "
                       "valor_unitario) VALUES (?, ?, ?, ?, ?, ?)", (oid, t, item, d, q, v))
            if t == P:
                mov(item, "saida", -q, f"OS-{seq:04d}", ab, oid, resp)
        for h, dias in hist:
            db.execute("INSERT INTO os_historico (os_id, status, data, usuario_id) "
                       "VALUES (?, ?, ?, ?)", (oid, h, DT(dias, 14), resp))

    for item, saldo in saldos.items():
        db.execute("UPDATE itens_estoque SET quantidade = ? WHERE id = ?", (saldo, item))

    # ---------------------------------------------------------------- financeiro
    receber = [
        (82, "Instalação de rede — 2ª parcela", MARIANA, None, 280.00, -9, None, "Boleto"),
        (83, f"Contrato de suporte mensal — {mes}", TECH, None, 1450.00, -19, -20, "Pix"),
        (84, "Limpeza interna — OS-0229", CLINICA, 229, 169.90, -11, -19, "Pix"),
        (85, "Configuração de impressora", RAFAEL, None, 120.00, 6, None, "Pix"),
        (86, "Diagnóstico técnico — OS-0232", PADARIA, 232, 80.00, -5, -6, "Cartão de débito"),
        (87, f"Contrato de suporte mensal — {mes}", MOURA, None, 890.00, -14, None, "Boleto"),
        (88, "Manutenção preventiva — OS-0233", TECH, 233, 1019.40, 22, None, "Boleto"),
    ]
    for seq, desc, cli, os_seq, valor, venc, pago, forma in receber:
        db.execute("INSERT INTO contas (tipo, seq, descricao, cliente_id, os_id, categoria, valor, "
                   "vencimento, forma_pagamento, pago_em, criado_em, criado_por) "
                   "VALUES ('receber', ?, ?, ?, ?, 'Serviços', ?, ?, ?, ?, ?, ?)",
                   (seq, desc, cli, os_ids.get(os_seq), valor, D(venc), forma,
                    D(pago) if pago is not None else None, DT(min(venc, -1) - 15), ADM))

    pagar = [
        (37, "Energia elétrica", "Enel", "Utilidades", 412.35, -12, -13, "Boleto"),
        (38, "Honorários contábeis", "Silva & Associados Contabilidade", "Serviços", 750.00, 6,
         None, None),
        (39, "Internet empresarial", "Vivo Empresas", "Utilidades", 289.90, -4, None, None),
        (40, f"Aluguel da loja — {mes}", "Imobiliária Central", "Aluguel", 3200.00, -14, -15,
         "Transferência"),
        (41, "Compra de SSDs — NF 4532", "Kingston Distribuidora", "Fornecedores", 2299.20, 4,
         None, None),
    ]
    for seq, desc, forn, cat, valor, venc, pago, forma in pagar:
        db.execute("INSERT INTO contas (tipo, seq, descricao, fornecedor, categoria, valor, "
                   "vencimento, forma_pagamento, pago_em, criado_em, criado_por) "
                   "VALUES ('pagar', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (seq, desc, forn, cat, valor, D(venc), forma,
                    D(pago) if pago is not None else None, DT(-30), ADM))

    assert all(len(so_digitos(c[1])) in (11, 14) for c in clientes)
