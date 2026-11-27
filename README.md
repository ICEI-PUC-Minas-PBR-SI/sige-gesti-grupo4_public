# GesTI

**Sistema Integrado de Gestão para Micro e Pequenas Empresas de Serviços em Tecnologia da Informação: um estudo de caso aplicado à NexaHertz**

Trabalho Interdisciplinar de Sistemas Integrados de Gestão Empresarial (SIGE)
PUC Minas - Sistemas de Informação - Campus Barreiro
Professor Dr. Paulo Isnard

## Grupo 4

- Ana Clara Vieira Rodrigues
- Brian Nicolas Dias Costa
- Diogo Evangelista Pacheco
- Gabriel Santos Valgas de Araujo
- Jennifer Caroline Castro Silva
- Laura Santiago Novais
- Livia Helen Pereira Almeira
- Matheus Filipe Alves

## Sobre o projeto

O GesTI reúne em um único ambiente o cadastro de clientes, orçamentos e ordens de serviço, o controle de estoque de peças e equipamentos e a gestão financeira básica (contas a pagar e a receber) de micro e pequenas empresas prestadoras de serviços de TI. A NexaHertz é o estudo de caso.

## Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| `docs/cronograma/` | Cronograma de atividades internas e externas da disciplina |
| `docs/etapa1/` | Etapa 1: tema, título e introdução |
| `docs/etapa2/` | Etapa 2: introdução, problemática, justificativa, objetivos e esboço do protótipo |
| `prototipo/` | Protótipo navegável (`interativo/`) e capturas das telas (`telas/`) |
| `src/` | Etapa 4: código-fonte do aplicativo (Python + Flask + SQLite) |

## Cronograma de entregas

| Data | Etapa | Entrega |
|---|---|---|
| 28/08 | 1ª | Tema, título e introdução |
| 25/09 | 2ª | Introdução + problemática + justificativa + objetivos + esboço do protótipo |
| 30/10 | 3ª | Anterior + referencial teórico + protótipo do app + requisitos |
| 27/11 | 4ª | Anterior + metodologia + versão inicial do app |
| 11/12 | 5ª | Versão final do app, mostra tecnológica e apresentação final (demo) |

## Protótipo

Protótipo navegável e capturas das telas em [prototipo/](prototipo/README.md).

## Aplicativo (Etapa 4)

Versão inicial do sistema, desenvolvida a partir das telas do protótipo. Para rodar:

```bash
cd src
python -m pip install -r requirements.txt
python run.py
```

Abra http://127.0.0.1:5000 e entre com `rodrigo@nexahertz.com.br` / `gesti123`. As instruções completas, a estrutura do código, o modelo de dados e os requisitos atendidos estão em [src/README.md](src/README.md).

## Como colaborar

1. Antes de começar, atualize seu repositório local (`git pull`).
2. Crie uma branch para o que for trabalhar (`git checkout -b docs/etapa3-referencial`).
3. Faça commits pequenos e com mensagem clara.
4. Abra um Pull Request para a `main` e peça revisão de outro integrante.
