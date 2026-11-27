-- GesTI - modelo de dados (SQLite)
-- Uma base relacional única para todos os módulos (RNF-17).

PRAGMA foreign_keys = ON;

CREATE TABLE usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    senha_hash    TEXT    NOT NULL,
    perfil        TEXT    NOT NULL CHECK (perfil IN ('admin', 'tecnico', 'atendente')),
    ativo         INTEGER NOT NULL DEFAULT 1,
    criado_em     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE clientes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome           TEXT    NOT NULL,
    documento      TEXT    UNIQUE,              -- CPF ou CNPJ, só dígitos
    contato        TEXT,
    email          TEXT,
    telefone       TEXT,
    cep            TEXT,
    endereco       TEXT,
    numero         TEXT,
    complemento    TEXT,
    cidade         TEXT,
    uf             TEXT,
    status         TEXT    NOT NULL DEFAULT 'ativo' CHECK (status IN ('ativo', 'inativo')),
    anotacoes      TEXT,
    criado_em      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    criado_por     INTEGER REFERENCES usuarios (id),
    atualizado_em  TEXT,
    atualizado_por INTEGER REFERENCES usuarios (id)
);

-- Equipamentos do cliente, reaproveitados em orçamentos e OS (RF-10)
CREATE TABLE equipamentos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id    INTEGER NOT NULL REFERENCES clientes (id),
    tipo          TEXT    NOT NULL,
    marca_modelo  TEXT,
    numero_serie  TEXT,
    criado_em     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Catálogo de serviços usado no "+ Adicionar serviço"
CREATE TABLE servicos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao  TEXT    NOT NULL,
    preco      REAL    NOT NULL CHECK (preco >= 0),
    ativo      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE itens_estoque (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sku             TEXT    NOT NULL UNIQUE,
    descricao       TEXT    NOT NULL,
    categoria       TEXT    NOT NULL,
    quantidade      INTEGER NOT NULL DEFAULT 0 CHECK (quantidade >= 0),   -- RN-04
    estoque_minimo  INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    preco           REAL    NOT NULL DEFAULT 0 CHECK (preco >= 0),
    fornecedor      TEXT,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    criado_por      INTEGER REFERENCES usuarios (id),
    atualizado_em   TEXT,
    atualizado_por  INTEGER REFERENCES usuarios (id)
);

CREATE TABLE orcamentos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    seq            INTEGER NOT NULL UNIQUE,      -- exibido como ORC-0000
    cliente_id     INTEGER NOT NULL REFERENCES clientes (id),
    equipamento_id INTEGER REFERENCES equipamentos (id),
    descricao      TEXT    NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'rascunho'
                   CHECK (status IN ('rascunho', 'enviado', 'aprovado', 'recusado', 'os', 'faturado')),
    desconto       REAL    NOT NULL DEFAULT 0 CHECK (desconto >= 0),
    validade       TEXT    NOT NULL,             -- data (AAAA-MM-DD)
    condicoes      TEXT,
    observacoes    TEXT,
    criado_em      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    criado_por     INTEGER REFERENCES usuarios (id),
    atualizado_em  TEXT,
    atualizado_por INTEGER REFERENCES usuarios (id)
);

CREATE TABLE orcamento_itens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id    INTEGER NOT NULL REFERENCES orcamentos (id) ON DELETE CASCADE,
    tipo            TEXT    NOT NULL CHECK (tipo IN ('servico', 'peca', 'avulso')),
    item_estoque_id INTEGER REFERENCES itens_estoque (id),
    descricao       TEXT    NOT NULL,
    quantidade      REAL    NOT NULL CHECK (quantidade > 0),
    valor_unitario  REAL    NOT NULL CHECK (valor_unitario >= 0)
);

-- Data de cada mudança de situação do orçamento (RF-16)
CREATE TABLE orcamento_historico (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id  INTEGER NOT NULL REFERENCES orcamentos (id) ON DELETE CASCADE,
    status        TEXT    NOT NULL,
    data          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    usuario_id    INTEGER REFERENCES usuarios (id)
);

CREATE TABLE ordens_servico (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    seq             INTEGER NOT NULL UNIQUE,     -- exibido como OS-0000
    cliente_id      INTEGER NOT NULL REFERENCES clientes (id),
    orcamento_id    INTEGER UNIQUE REFERENCES orcamentos (id),
    equipamento_id  INTEGER REFERENCES equipamentos (id),
    titulo          TEXT    NOT NULL,
    equip_tipo      TEXT,
    equip_modelo    TEXT,
    equip_serie     TEXT,
    equip_acessorios TEXT,
    problema        TEXT,
    laudo           TEXT,
    observacoes     TEXT,
    responsavel_id  INTEGER REFERENCES usuarios (id),
    status          TEXT    NOT NULL DEFAULT 'aberta'
                    CHECK (status IN ('aberta', 'andamento', 'aguardando', 'concluida')),
    desconto        REAL    NOT NULL DEFAULT 0 CHECK (desconto >= 0),
    abertura        TEXT    NOT NULL,
    previsao        TEXT,
    conclusao       TEXT,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    criado_por      INTEGER REFERENCES usuarios (id),
    atualizado_em   TEXT,
    atualizado_por  INTEGER REFERENCES usuarios (id)
);

CREATE TABLE os_itens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    os_id           INTEGER NOT NULL REFERENCES ordens_servico (id) ON DELETE CASCADE,
    tipo            TEXT    NOT NULL CHECK (tipo IN ('servico', 'peca', 'avulso')),
    item_estoque_id INTEGER REFERENCES itens_estoque (id),
    descricao       TEXT    NOT NULL,
    quantidade      REAL    NOT NULL CHECK (quantidade > 0),
    valor_unitario  REAL    NOT NULL CHECK (valor_unitario >= 0)
);

CREATE TABLE os_historico (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    os_id       INTEGER NOT NULL REFERENCES ordens_servico (id) ON DELETE CASCADE,
    status      TEXT    NOT NULL,
    data        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    usuario_id  INTEGER REFERENCES usuarios (id)
);

-- Histórico de movimentações do estoque (RF-30, RF-31)
CREATE TABLE movimentacoes_estoque (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL REFERENCES itens_estoque (id),
    tipo        TEXT    NOT NULL CHECK (tipo IN ('entrada', 'saida', 'ajuste')),
    quantidade  INTEGER NOT NULL,                -- com sinal (+ entra, - sai)
    saldo       INTEGER NOT NULL,                -- saldo após a movimentação
    referencia  TEXT,
    os_id       INTEGER REFERENCES ordens_servico (id),
    data        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    usuario_id  INTEGER REFERENCES usuarios (id)
);

-- Contas a receber e a pagar (RF-34 a RF-39)
CREATE TABLE contas (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo             TEXT    NOT NULL CHECK (tipo IN ('receber', 'pagar')),
    seq              INTEGER NOT NULL,           -- CR-0000 / CP-0000
    descricao        TEXT    NOT NULL,
    cliente_id       INTEGER REFERENCES clientes (id),
    fornecedor       TEXT,
    os_id            INTEGER UNIQUE REFERENCES ordens_servico (id),   -- RN-06
    categoria        TEXT,
    valor            REAL    NOT NULL CHECK (valor > 0),
    vencimento       TEXT    NOT NULL,
    forma_pagamento  TEXT,
    pago_em          TEXT,
    criado_em        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    criado_por       INTEGER REFERENCES usuarios (id),
    atualizado_em    TEXT,
    atualizado_por   INTEGER REFERENCES usuarios (id),
    UNIQUE (tipo, seq)
);

CREATE INDEX idx_orcamentos_cliente ON orcamentos (cliente_id);
CREATE INDEX idx_os_cliente         ON ordens_servico (cliente_id);
CREATE INDEX idx_os_status          ON ordens_servico (status);
CREATE INDEX idx_mov_item           ON movimentacoes_estoque (item_id);
CREATE INDEX idx_contas_tipo        ON contas (tipo, vencimento);
CREATE INDEX idx_contas_cliente     ON contas (cliente_id);
