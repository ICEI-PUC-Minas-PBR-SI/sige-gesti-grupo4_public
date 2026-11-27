"""Testes do fluxo integrado e das regras de negócio.

Rodar a partir de src/:  python -m unittest discover -s tests -v
"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gesti import create_app  # noqa: E402
from gesti.db import get_db  # noqa: E402
from gesti.util import cnpj_valido, cpf_valido, moeda, parse_valor  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        self.app = create_app({"TESTING": True, "DATABASE": self.db_path, "CSRF_ENABLED": False,
                               "SECRET_KEY": "teste"})
        self.c = self.app.test_client()

    def tearDown(self):
        os.remove(self.db_path)

    def login(self, email="rodrigo@nexahertz.com.br", senha="gesti123"):
        return self.c.post("/login", data={"email": email, "senha": senha})

    def one(self, sql, params=()):
        with self.app.app_context():
            return get_db().execute(sql, params).fetchone()


class TestUtil(unittest.TestCase):
    def test_moeda_e_valor(self):
        self.assertEqual(moeda(1234.5), "R$ 1.234,50")
        self.assertEqual(parse_valor("1.234,56"), 1234.56)
        self.assertEqual(parse_valor("19.9"), 19.9)

    def test_documentos(self):
        self.assertTrue(cpf_valido("529.982.247-25"))
        self.assertFalse(cpf_valido("111.111.111-11"))
        self.assertTrue(cnpj_valido("11.444.777/0001-61"))
        self.assertFalse(cnpj_valido("11.444.777/0001-62"))


class TestAcesso(Base):
    def test_exige_login(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])

    def test_login_invalido(self):
        r = self.login(senha="errada")
        self.assertIn("incorretos", r.get_data(as_text=True))

    def test_senha_com_hash(self):
        u = self.one("SELECT senha_hash FROM usuarios LIMIT 1")
        self.assertNotIn("gesti123", u["senha_hash"])

    def test_todas_as_telas_abrem(self):
        self.login()
        for url in ["/", "/clientes/", "/clientes/novo", "/clientes/1", "/clientes/1?aba=os",
                    "/clientes/1?aba=financeiro", "/clientes/1?aba=equipamentos",
                    "/orcamentos/", "/orcamentos/novo", "/orcamentos/7", "/orcamentos/7/imprimir",
                    "/os/", "/os/?modo=lista", "/os/nova", "/os/7", "/estoque/", "/estoque/novo",
                    "/estoque/2", "/financeiro/", "/financeiro/?tipo=pagar", "/busca/?q=ssd",
                    "/relatorios/", "/configuracoes/", "/financeiro/exportar.csv",
                    "/relatorios/estoque.csv", "/relatorios/os.csv"]:
            with self.subTest(url=url):
                self.assertEqual(self.c.get(url).status_code, 200)

    def test_tecnico_nao_acessa_financeiro(self):
        """RF-02 / RNF-11: bloqueio no servidor, não só na interface."""
        self.login("ana@nexahertz.com.br")
        self.assertEqual(self.c.get("/financeiro/").status_code, 403)
        self.assertEqual(self.c.post("/financeiro/1/pagar", data={}).status_code, 403)
        self.assertEqual(self.c.get("/os/").status_code, 200)


class TestClientes(Base):
    def test_valida_e_impede_duplicado(self):
        self.login()
        r = self.c.post("/clientes/novo", data={"nome": "X", "documento": "123", "email": "x@",
                                                 "telefone": "12", "cep": "1"})
        t = r.get_data(as_text=True)
        for msg in ("Informe um CPF", "E-mail inválido", "Telefone inválido", "CEP inválido"):
            self.assertIn(msg, t)
        doc = self.one("SELECT documento FROM clientes WHERE id = 1")["documento"]
        r = self.c.post("/clientes/novo", data={"nome": "Outro", "documento": doc})
        self.assertIn("já está cadastrado", r.get_data(as_text=True))

    def test_cria_cliente(self):
        self.login()
        r = self.c.post("/clientes/novo", data={"nome": "Escola Nova", "documento": "11.444.777/0001-61",
                                                 "email": "ti@escola.com.br", "telefone": "(31) 98888-1234",
                                                 "cep": "30130-110", "status": "ativo"})
        self.assertEqual(r.status_code, 302)
        self.assertIsNotNone(self.one("SELECT 1 FROM clientes WHERE documento = '11444777000161'"))

    def test_nao_exclui_com_movimentacao(self):
        """RN-07."""
        self.login()
        self.c.post("/clientes/1/excluir")
        self.assertIsNotNone(self.one("SELECT 1 FROM clientes WHERE id = 1"))


class TestFluxoIntegrado(Base):
    """Cliente → orçamento → OS → baixa no estoque → conta a receber → pagamento."""

    def test_fluxo_completo(self):
        self.login()
        ssd = self.one("SELECT * FROM itens_estoque WHERE sku = 'SSD-480-KA4'")
        saldo_inicial = ssd["quantidade"]

        itens = [{"tipo": "servico", "descricao": "Troca de SSD", "quantidade": 1, "valor_unitario": 160},
                 {"tipo": "peca", "item_estoque_id": ssd["id"], "descricao": ssd["descricao"],
                  "quantidade": 2, "valor_unitario": 290}]
        # RN-03: desconto maior que o subtotal é recusado
        r = self.c.post("/orcamentos/novo", data={"cliente_id": 2, "descricao": "Teste",
                                                   "itens_json": json.dumps(itens), "desconto": "9999"})
        self.assertIn("desconto não pode ser maior", r.get_data(as_text=True))

        r = self.c.post("/orcamentos/novo", data={"cliente_id": 2, "descricao": "Troca de 2 SSDs",
                                                   "itens_json": json.dumps(itens), "desconto": "40,00",
                                                   "validade_dias": "15", "acao": "enviar"})
        orc_id = int(re.search(r"/orcamentos/(\d+)", r.headers["Location"]).group(1))
        orc = self.one("SELECT * FROM orcamentos WHERE id = ?", (orc_id,))
        self.assertEqual(orc["status"], "enviado")

        # RN-02: não converte antes de aprovar
        self.c.post(f"/orcamentos/{orc_id}/gerar-os")
        self.assertIsNone(self.one("SELECT 1 FROM ordens_servico WHERE orcamento_id = ?", (orc_id,)))

        self.c.post(f"/orcamentos/{orc_id}/status", data={"status": "aprovado"})
        r = self.c.post(f"/orcamentos/{orc_id}/gerar-os", data={"responsavel_id": 2})
        os_row = self.one("SELECT * FROM ordens_servico WHERE orcamento_id = ?", (orc_id,))
        self.assertIsNotNone(os_row)
        self.assertEqual(self.one("SELECT COUNT(*) AS n FROM os_itens WHERE os_id = ?", (os_row["id"],))["n"], 2)

        # RF-25: baixa automática no estoque
        self.assertEqual(self.one("SELECT quantidade FROM itens_estoque WHERE id = ?", (ssd["id"],))["quantidade"],
                         saldo_inicial - 2)

        # remover a peça devolve ao estoque; adicionar de novo baixa
        peca = self.one("SELECT id FROM os_itens WHERE os_id = ? AND tipo = 'peca'", (os_row["id"],))
        self.c.post(f"/os/{os_row['id']}/itens/{peca['id']}/remover")
        self.assertEqual(self.one("SELECT quantidade FROM itens_estoque WHERE id = ?", (ssd["id"],))["quantidade"],
                         saldo_inicial)
        self.c.post(f"/os/{os_row['id']}/itens", data={"tipo": "peca", "item_id": ssd["id"], "quantidade": 2})

        # RN-04: saldo não pode ficar negativo
        self.c.post(f"/os/{os_row['id']}/itens", data={"tipo": "peca", "item_id": ssd["id"], "quantidade": 999})
        self.assertGreaterEqual(self.one("SELECT quantidade FROM itens_estoque WHERE id = ?", (ssd["id"],))["quantidade"], 0)

        # kanban: muda situação via JSON
        r = self.c.post(f"/os/{os_row['id']}/status", json={"status": "andamento"})
        self.assertEqual(r.status_code, 200)

        # RF-26: concluir gera a conta a receber (total = 160 + 2×290 − 40 = 700)
        self.c.post(f"/os/{os_row['id']}/finalizar", data={"forma_pagamento": "Pix", "vencimento": "2099-01-01"})
        conta = self.one("SELECT * FROM contas WHERE os_id = ?", (os_row["id"],))
        self.assertAlmostEqual(conta["valor"], 700.0)
        self.assertEqual(self.one("SELECT status FROM orcamentos WHERE id = ?", (orc_id,))["status"], "faturado")

        # RN-06: reabrir e concluir de novo não duplica a conta
        self.c.post(f"/os/{os_row['id']}/status", data={"status": "andamento"})
        self.c.post(f"/os/{os_row['id']}/finalizar", data={"forma_pagamento": "Pix", "vencimento": "2099-01-01"})
        self.assertEqual(self.one("SELECT COUNT(*) AS n FROM contas WHERE os_id = ?", (os_row["id"],))["n"], 1)

        # RF-37: marcar como pago
        self.c.post(f"/financeiro/{conta['id']}/pagar", data={"forma_pagamento": "Pix", "tipo": "receber"})
        self.assertIsNotNone(self.one("SELECT pago_em FROM contas WHERE id = ?", (conta["id"],))["pago_em"])

    def test_rn09_tecnico_nao_altera_os_concluida(self):
        self.login("ana@nexahertz.com.br")
        os_id = self.one("SELECT id FROM ordens_servico WHERE status = 'concluida' LIMIT 1")["id"]
        self.c.post(f"/os/{os_id}/status", data={"status": "andamento"})
        self.assertEqual(self.one("SELECT status FROM ordens_servico WHERE id = ?", (os_id,))["status"], "concluida")

    def test_transacao_desfaz_tudo(self):
        """RNF-14: falha no meio da conversão não deixa OS pela metade."""
        self.login()
        orc_id = self.one("SELECT id FROM orcamentos WHERE seq = 148")["id"]
        self.c.post(f"/orcamentos/{orc_id}/status", data={"status": "aprovado"})
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE itens_estoque SET quantidade = 0 WHERE sku = 'SSD-480-KA4'")
            db.commit()
        n_antes = self.one("SELECT COUNT(*) AS n FROM ordens_servico")["n"]
        self.c.post(f"/orcamentos/{orc_id}/gerar-os")
        self.assertEqual(self.one("SELECT COUNT(*) AS n FROM ordens_servico")["n"], n_antes)
        self.assertEqual(self.one("SELECT status FROM orcamentos WHERE id = ?", (orc_id,))["status"], "aprovado")


class TestEstoque(Base):
    def test_movimentacoes(self):
        self.login()
        self.c.post("/estoque/2/movimentar", data={"tipo_mov": "entrada", "quantidade": 10, "referencia": "NF 1"})
        self.c.post("/estoque/2/movimentar", data={"tipo_mov": "saida", "quantidade": 3})
        self.c.post("/estoque/2/movimentar", data={"tipo_mov": "ajuste", "quantidade": 7})
        self.assertEqual(self.one("SELECT quantidade FROM itens_estoque WHERE id = 2")["quantidade"], 7)
        ult = self.one("SELECT * FROM movimentacoes_estoque WHERE item_id = 2 ORDER BY id DESC LIMIT 1")
        self.assertEqual((ult["tipo"], ult["saldo"]), ("ajuste", 7))

    def test_sku_automatico(self):
        self.login()
        self.c.post("/estoque/novo", data={"descricao": "Mouse sem fio Logitech", "categoria": "Periféricos",
                                           "estoque_minimo": 2, "preco": "79,90", "quantidade": 5})
        i = self.one("SELECT * FROM itens_estoque WHERE descricao = 'Mouse sem fio Logitech'")
        self.assertTrue(i["sku"])
        self.assertEqual(i["quantidade"], 5)


if __name__ == "__main__":
    unittest.main()
