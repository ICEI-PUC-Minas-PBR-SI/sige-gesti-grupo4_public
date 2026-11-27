# GesTI – Requisitos Funcionais e Não Funcionais

> 3ª etapa · entrega em 30/10/2026 · [voltar ao README](../../README.md)

## 1 Introdução

Este documento define 61 requisitos do GesTI (43 funcionais e 18 não funcionais), além de 9 regras de negócio, derivados da Etapa 2 e das 13 telas do protótipo, para a 3ª etapa do trabalho de SIGE (entrega em 30/10).

**Objetivo.** Especificar o que o GesTI deve fazer e com que qualidade, para micro e pequenas empresas de serviços de TI, tendo a NexaHertz como estudo de caso.

**Escopo.** Cinco módulos integrados em uma base única: Clientes, Orçamentos, Ordens de Serviço (OS), Estoque e Financeiro (contas a pagar e a receber), mais um Dashboard consolidado.

**Perfis de usuário** (assumidos a partir do protótipo; a validar com a NexaHertz):

| Perfil | Descrição |
| --- | --- |
| Administrador / proprietário | Acesso total; gerencia usuários, vê o financeiro e os indicadores |
| Técnico | Atende OS, registra serviços e peças usadas, consulta clientes e estoque |
| Atendente / comercial | Cadastra clientes, emite orçamentos e acompanha OS |

**Convenções.** RF-xx = requisito funcional; RNF-xx = requisito não funcional; RN-xx = regra de negócio. Prioridade pelo método MoSCoW: **M** (essencial), **S** (importante), **C** (desejável).

## 2 Requisitos funcionais

Os requisitos estão agrupados por módulo, na ordem do fluxo integrado: cliente, orçamento, OS, estoque e financeiro.

### 2.1 Acesso e recursos gerais

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF-01 | O sistema deve autenticar usuários por e-mail e senha antes de dar acesso a qualquer módulo. | M |
| RF-02 | O sistema deve controlar permissões por perfil (administrador, técnico, atendente); por exemplo, apenas o administrador acessa o Financeiro. | S |
| RF-03 | O sistema deve oferecer busca global por clientes, OS e orçamentos a partir de qualquer tela. | S |
| RF-04 | O sistema deve registrar autoria e data de criação e alteração dos principais registros (cliente, orçamento, OS, movimentação, conta). | S |

### 2.2 Clientes

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF-05 | O sistema deve cadastrar cliente (pessoa física ou jurídica) com nome, CPF/CNPJ, e-mail, telefone, endereço (CEP, rua, complemento, cidade), status e anotações internas. | M |
| RF-06 | O sistema deve validar o formato de CPF/CNPJ, e-mail, telefone e CEP e impedir CPF/CNPJ duplicado. | M |
| RF-07 | O sistema deve editar e inativar clientes, preservando o histórico de quem possui movimentação. | M |
| RF-08 | O sistema deve listar clientes com busca por nome, CPF/CNPJ ou e-mail e filtros por status e cidade. | M |
| RF-09 | O sistema deve exibir, na ficha do cliente, o histórico de relacionamento: orçamentos, OS e movimentações financeiras associados. | M |
| RF-10 | O sistema deve manter os equipamentos de cada cliente, para reaproveitá-los em novos orçamentos e OS sem redigitar. | S |
| RF-11 | O sistema deve permitir iniciar um novo orçamento ou OS diretamente da ficha do cliente. | C |

### 2.3 Orçamentos

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF-12 | O sistema deve criar orçamento vinculado a um cliente cadastrado, com número gerado automaticamente. | M |
| RF-13 | O sistema deve permitir incluir no orçamento serviços (descrição, quantidade, valor unitário) e peças selecionadas do estoque. | M |
| RF-14 | O sistema deve calcular automaticamente subtotal, desconto e total do orçamento. | M |
| RF-15 | O sistema deve registrar equipamento, validade, condições (prazo, garantia) e observações no orçamento. | M |
| RF-16 | O sistema deve controlar a situação do orçamento nas etapas Rascunho, Enviado ao cliente, Aprovado, Ordem de serviço e Faturado, registrando a data de cada mudança. | M |
| RF-17 | O sistema deve converter um orçamento aprovado em OS, copiando cliente, equipamento, serviços e peças sem nova digitação. | M |
| RF-18 | O sistema deve listar orçamentos com busca por número ou cliente e filtro por situação. | M |
| RF-19 | O sistema deve gerar o orçamento em PDF para envio ao cliente (e-mail ou aplicativo de mensagens). | S |

### 2.4 Ordens de serviço

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF-20 | O sistema deve criar OS a partir de um orçamento aprovado ou diretamente (avulsa), com número gerado automaticamente. | M |
| RF-21 | O sistema deve registrar na OS o equipamento recebido, o problema relatado, o serviço realizado (laudo), o responsável técnico e as datas de abertura e previsão. | M |
| RF-22 | O sistema deve controlar a situação da OS em Aberta, Em andamento, Aguardando e Concluída, registrando o histórico de mudanças. | M |
| RF-23 | O sistema deve exibir as OS em lista e em quadro (kanban) organizado por situação, permitindo alterar a situação pelo quadro. | M |
| RF-24 | O sistema deve permitir registrar serviços executados e peças utilizadas na OS, com valores e totais calculados automaticamente. | M |
| RF-25 | O sistema deve dar baixa automática no estoque das peças lançadas na OS e devolvê-las ao estoque quando removidas. | M |
| RF-26 | O sistema deve gerar a conta a receber correspondente ao concluir a OS, com valor, cliente e forma de pagamento. | M |
| RF-27 | O sistema deve listar OS com busca por número, cliente ou serviço e filtros por situação e responsável. | M |

### 2.5 Estoque

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF-28 | O sistema deve cadastrar itens de peças e equipamentos com descrição, categoria, código (SKU, gerado se vazio), quantidade, estoque mínimo, preço e fornecedor. | M |
| RF-29 | O sistema deve classificar cada item como Em estoque, Estoque baixo (quantidade ≤ mínimo) ou Sem estoque (quantidade = 0), de forma automática. | M |
| RF-30 | O sistema deve registrar entradas (com documento, ex.: nota fiscal, e fornecedor), saídas e ajustes de inventário, atualizando o saldo. | M |
| RF-31 | O sistema deve manter o histórico de movimentações de cada item, indicando a OS ou o lançamento de origem. | M |
| RF-32 | O sistema deve listar itens com busca por produto ou SKU e filtros por categoria e situação. | M |
| RF-33 | O sistema deve alertar itens com estoque baixo ou zerado, no Dashboard e no momento de usá-los em orçamento ou OS. | S |

### 2.6 Financeiro

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF-34 | O sistema deve gerar a conta a receber automaticamente a partir da OS concluída (ver RF-26). | M |
| RF-35 | O sistema deve permitir cadastrar contas a pagar com descrição, fornecedor, valor, vencimento e categoria. | M |
| RF-36 | O sistema deve permitir lançar manualmente contas a receber não originadas de OS. | S |
| RF-37 | O sistema deve registrar o pagamento ou recebimento pela ação "Marcar como pago", com data e forma de pagamento (Pix, boleto, cartão de crédito etc.). | M |
| RF-38 | O sistema deve identificar automaticamente contas em atraso (vencimento anterior à data atual e não pagas). | M |
| RF-39 | O sistema deve listar contas a receber e a pagar com filtros por situação e período e indicadores de valor em aberto, recebido no mês e em atraso. | M |

### 2.7 Dashboard e relatórios

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF-40 | O sistema deve exibir indicadores: OS abertas, orçamentos aguardando aprovação, contas a receber e itens com estoque baixo. | M |
| RF-41 | O sistema deve exibir OS e orçamentos recentes, resumo financeiro do mês e alertas de estoque. | S |
| RF-42 | O sistema deve oferecer atalhos para criar cliente, orçamento e OS a partir do Dashboard. | S |
| RF-43 | O sistema deve exportar listagens e o resumo financeiro em PDF ou planilha (CSV/XLSX). | C |

## 3 Regras de negócio e fluxo integrado

Cada informação é cadastrada uma só vez e reaproveitada nas etapas seguintes, no fluxo abaixo.

1. O cliente é cadastrado (RF-05).
2. A partir dele, emite-se o orçamento com serviços e peças do estoque (RF-12, RF-13).
3. O orçamento aprovado gera a OS (RF-17).
4. As peças usadas na OS dão baixa automática no estoque (RF-25).
5. Ao concluir a OS, gera-se a conta a receber (RF-26).
6. O recebimento é registrado no Financeiro (RF-37) e alimenta o Dashboard (RF-40).

| ID | Regra |
| --- | --- |
| RN-01 | Dados de cliente e equipamento não são redigitados entre orçamento, OS e financeiro; são herdados do cadastro. |
| RN-02 | Somente orçamento com situação Aprovado pode ser convertido em OS. |
| RN-03 | O total do orçamento e da OS = soma de serviços e peças − desconto; o desconto não pode exceder o subtotal. |
| RN-04 | A baixa de estoque ocorre quando a peça é lançada na OS; o saldo não pode ficar negativo. |
| RN-05 | Um item está em Estoque baixo quando quantidade ≤ estoque mínimo e Sem estoque quando quantidade = 0. |
| RN-06 | Cada OS concluída gera uma única conta a receber; reabrir e concluir de novo não duplica a conta. |
| RN-07 | Cliente com orçamentos, OS ou lançamentos não é excluído, apenas inativado. |
| RN-08 | Conta está em atraso quando o vencimento é anterior à data atual e ela não foi marcada como paga. |
| RN-09 | OS concluída só pode ser alterada pelo administrador (regra proposta, a confirmar com a NexaHertz). |

## 4 Requisitos não funcionais

Organizados pelas características de qualidade da ISO/IEC 25010. As metas numéricas são propostas para uma microempresa com poucos usuários simultâneos e devem ser validadas com a NexaHertz.

| ID | Categoria | Requisito | Prioridade |
| --- | --- | --- | --- |
| RNF-01 | Usabilidade | A interface deve usar o vocabulário do serviço de TI (equipamento recebido, defeito relatado, laudo, peças aplicadas). | M |
| RNF-02 | Usabilidade | Um usuário sem treinamento formal deve conseguir cadastrar cliente, emitir orçamento e abrir OS em até 10 minutos, após uma breve apresentação. | S |
| RNF-03 | Usabilidade | A navegação entre os cinco módulos deve ser feita por menu fixo, com qualquer funcionalidade principal a no máximo 3 cliques do Dashboard. | S |
| RNF-04 | Usabilidade | Mensagens de erro e validação devem ser em português, indicar o campo e como corrigir. | M |
| RNF-05 | Usabilidade | Valores monetários devem seguir o formato brasileiro (R\$ 1.234,56) e datas, dd/mm/aaaa. | M |
| RNF-06 | Desempenho | Telas de listagem e consultas devem responder em até 2 segundos com até 5.000 registros por módulo. | S |
| RNF-07 | Desempenho | Operações de gravação (salvar orçamento, OS, pagamento) devem concluir em até 3 segundos. | S |
| RNF-08 | Desempenho | O sistema deve suportar ao menos 10 usuários simultâneos sem degradação perceptível. | S |
| RNF-09 | Segurança | Senhas devem ser armazenadas com hash e salt (ex.: bcrypt), nunca em texto puro. | M |
| RNF-10 | Segurança | A comunicação entre navegador e servidor deve usar HTTPS, e a sessão deve expirar após período de inatividade (ex.: 30 min). | M |
| RNF-11 | Segurança | O acesso a cada função e dado deve ser validado no servidor conforme o perfil do usuário, e não apenas ocultado na interface. | M |
| RNF-12 | Conformidade legal | O tratamento de dados pessoais de clientes (CPF/CNPJ, e-mail, telefone, endereço) deve seguir a LGPD: coleta mínima, finalidade informada e possibilidade de correção e anonimização. | M |
| RNF-13 | Confiabilidade | Deve haver backup automático diário do banco de dados, com retenção mínima de 7 dias e procedimento de restauração documentado. | M |
| RNF-14 | Confiabilidade | Operações que afetam mais de um módulo (concluir OS: baixa de estoque, conta a receber) devem ser transacionais: ou concluem por inteiro ou nada é gravado. | M |
| RNF-15 | Disponibilidade | O sistema deve estar disponível em pelo menos 95% do horário comercial (seg–sáb, 8h–18h). | S |
| RNF-16 | Compatibilidade | O sistema deve funcionar nas versões atuais do Chrome, Edge e Firefox, com layout responsivo para desktop, tablet e celular (uso pelo técnico em campo). | M |
| RNF-17 | Integridade de dados | Todos os módulos devem compartilhar uma única base relacional, com chaves estrangeiras que impeçam registros órfãos (ex.: OS sem cliente). | M |
| RNF-18 | Manutenibilidade | O código deve ser versionado em Git, organizado em camadas por módulo e acompanhado de documentação básica de instalação e do modelo de dados. | S |

## 5 Premissas, restrições e fora de escopo

**Premissas.** Os perfis de usuário, a regra RN-09 e as metas dos RNF são propostas deste levantamento, feito a partir dos documentos da Etapa 2 e do protótipo; ainda não foram validados em entrevista com a NexaHertz.

**Restrições.** Prazo: versão inicial do aplicativo em 27/11 e versão final em 11/12. Escopo enxuto, voltado a micro e pequenas empresas de serviços de TI, sem a amplitude de um ERP.

**Fora de escopo** (nesta versão): emissão de nota fiscal, conciliação bancária, folha de pagamento, contabilidade, integração com gateways de pagamento, aplicativo móvel nativo e portal de autoatendimento do cliente.

**Pontos em aberto para a NexaHertz.** Quais perfis de acesso existem de fato? Haverá mais de um técnico por OS? O envio de orçamento será por e-mail, WhatsApp ou ambos?