/* GesTI — comportamento da interface (sem dependências externas) */
(function () {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const csrf = () => ($('meta[name="csrf-token"]') || {}).content || '';

  const brl = (v) => 'R$ ' + (Number(v) || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const parseValor = (s) => {
    s = String(s ?? '').replace(/R\$|\s/g, '');
    if (s.includes(',')) s = s.replace(/\./g, '').replace(',', '.');
    const n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  };
  window.GesTI = { brl, parseValor };

  /* ---------- menu lateral no celular */
  $$('[data-toggle-nav]').forEach((b) => b.addEventListener('click', () => document.body.classList.toggle('nav-open')));
  document.addEventListener('click', (e) => {
    if (document.body.classList.contains('nav-open') && !e.target.closest('#sidebar') && !e.target.closest('[data-toggle-nav]')) {
      document.body.classList.remove('nav-open');
    }
  });

  /* ---------- busca global: Ctrl+K / Cmd+K (RF-03) */
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      const i = $('#busca-global');
      if (i) { e.preventDefault(); i.focus(); i.select(); }
    }
  });

  /* ---------- linhas clicáveis */
  $$('tr[data-href]').forEach((tr) => {
    tr.classList.add('click');
    tr.addEventListener('click', (e) => {
      if (e.target.closest('a, button, form, input, select')) return;
      window.location = tr.dataset.href;
    });
  });

  /* ---------- filtros que enviam o formulário ao mudar */
  $$('[data-autosubmit]').forEach((el) => el.addEventListener('change', () => el.form.submit()));

  /* ---------- diálogos */
  $$('[data-dialog]').forEach((b) => b.addEventListener('click', () => {
    const d = document.getElementById(b.dataset.dialog);
    if (!d) return;
    Object.entries(b.dataset).forEach(([k, v]) => {
      if (k.startsWith('set')) {
        const alvo = d.querySelector('[data-bind="' + k.slice(3).toLowerCase() + '"]');
        if (alvo) { if ('value' in alvo && alvo.tagName !== 'SPAN') alvo.value = v; else alvo.textContent = v; }
      }
    });
    if (b.dataset.action) d.querySelector('form').action = b.dataset.action;
    d.showModal();
  }));
  $$('dialog [data-close]').forEach((b) => b.addEventListener('click', () => b.closest('dialog').close()));
  $$('dialog[data-open-if]').forEach((d) => {
    if (new URLSearchParams(location.search).has(d.dataset.openIf)) d.showModal();
  });

  /* ---------- confirmação embutida (sem confirm()) */
  $$('form[data-confirm]').forEach((f) => {
    f.addEventListener('submit', (e) => {
      const b = f.querySelector('button[type="submit"], button:not([type])');
      if (f.dataset.ok === '1') return;
      e.preventDefault();
      f.dataset.ok = '1';
      if (b) { b.dataset.txt = b.textContent; b.textContent = f.dataset.confirm; }
      setTimeout(() => { f.dataset.ok = ''; if (b) b.textContent = b.dataset.txt; }, 4000);
    });
  });

  /* ---------- máscaras */
  const digitos = (s) => s.replace(/\D/g, '');
  const mascaras = {
    doc(v) {
      const d = digitos(v).slice(0, 14);
      if (d.length <= 11) return d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
      return d.replace(/^(\d{2})(\d)/, '$1.$2').replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3').replace(/\.(\d{3})(\d)/, '.$1/$2').replace(/(\d{4})(\d)/, '$1-$2');
    },
    tel(v) {
      const d = digitos(v).slice(0, 11);
      if (d.length <= 10) return d.replace(/^(\d{2})(\d)/, '($1) $2').replace(/(\d{4})(\d)/, '$1-$2');
      return d.replace(/^(\d{2})(\d)/, '($1) $2').replace(/(\d{5})(\d)/, '$1-$2');
    },
    cep(v) { return digitos(v).slice(0, 8).replace(/^(\d{5})(\d)/, '$1-$2'); },
  };
  $$('[data-mask]').forEach((i) => i.addEventListener('input', () => { i.value = mascaras[i.dataset.mask](i.value); }));

  /* ---------- CEP: preenche o endereço (ViaCEP, chamado pelo navegador) */
  const cep = $('[data-cep]');
  if (cep) {
    cep.addEventListener('blur', async () => {
      const d = digitos(cep.value);
      if (d.length !== 8) return;
      const hint = $('#cep-hint');
      try {
        if (hint) hint.textContent = 'Buscando endereço…';
        const r = await fetch('https://viacep.com.br/ws/' + d + '/json/');
        const j = await r.json();
        if (j.erro) { if (hint) hint.textContent = 'CEP não encontrado. Preencha o endereço manualmente.'; return; }
        const set = (n, v) => { const el = cep.form.elements[n]; if (el && !el.value && v) el.value = v; };
        set('endereco', j.logradouro); set('cidade', j.localidade); set('uf', j.uf);
        if (j.bairro && cep.form.elements.complemento && !cep.form.elements.complemento.value) cep.form.elements.complemento.placeholder = j.bairro;
        if (hint) hint.textContent = 'Endereço preenchido pelo CEP.';
        const num = cep.form.elements.numero; if (num) num.focus();
      } catch (_) {
        if (hint) hint.textContent = 'Não foi possível consultar o CEP agora. Preencha manualmente.';
      }
    });
  }

  /* ---------- exemplo no cadastro de cliente */
  const ex = $('[data-exemplo]');
  if (ex) ex.addEventListener('click', () => {
    const f = ex.closest('form') || $('form.cliente-form');
    const dados = JSON.parse(ex.dataset.exemplo);
    Object.entries(dados).forEach(([k, v]) => { if (f.elements[k]) f.elements[k].value = v; });
  });

  /* ---------- quadro (kanban) de OS: arrastar muda a situação (RF-23) */
  const quadro = $('.kanban[data-status-url]');
  if (quadro) {
    let arrastando = null;
    $$('.kcard', quadro).forEach((c) => {
      c.addEventListener('dragstart', (e) => { arrastando = c; c.classList.add('drag'); e.dataTransfer.effectAllowed = 'move'; });
      c.addEventListener('dragend', () => { c.classList.remove('drag'); arrastando = null; });
    });
    $$('.col', quadro).forEach((col) => {
      col.addEventListener('dragover', (e) => { e.preventDefault(); col.classList.add('over'); });
      col.addEventListener('dragleave', () => col.classList.remove('over'));
      col.addEventListener('drop', async (e) => {
        e.preventDefault(); col.classList.remove('over');
        if (!arrastando || arrastando.closest('.col') === col) return;
        const id = arrastando.dataset.id, status = col.dataset.status;
        if (status === 'concluida') { window.location = arrastando.getAttribute('href') + '?finalizar=1'; return; }
        const r = await fetch(quadro.dataset.statusUrl.replace('0', id), {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
          body: JSON.stringify({ status }),
        });
        const j = await r.json().catch(() => ({}));
        if (!r.ok) { mostrarErro(j.erro || 'Não foi possível mudar a situação.'); return; }
        window.location.reload();
      });
    });
  }

  function mostrarErro(msg) {
    const c = $('.content');
    const div = document.createElement('div');
    div.className = 'flash erro'; div.textContent = msg;
    c.prepend(div); window.scrollTo({ top: 0, behavior: 'smooth' });
    setTimeout(() => div.remove(), 6000);
  }

  /* ---------- montagem de itens do orçamento (RF-13, RF-14) */
  const builder = $('#orc-builder');
  if (builder) {
    const dados = JSON.parse($('#orc-dados').textContent);
    const pecas = Object.fromEntries(dados.pecas.map((p) => [String(p.id), p]));
    const servicos = Object.fromEntries(dados.servicos.map((s) => [String(s.id), s]));
    let itens = dados.itens || [];
    const corpo = $('#orc-itens'), vazio = $('#orc-vazio'), hidden = $('#itens_json');
    const desconto = $('#desconto');

    const render = () => {
      corpo.innerHTML = '';
      itens.forEach((it, idx) => {
        const row = document.createElement('div');
        row.className = 'item-row';
        const tagTxt = { servico: 'Serviço', peca: 'Peça', avulso: 'Avulso' }[it.tipo];
        let alerta = '';
        if (it.tipo === 'peca') {
          const p = pecas[String(it.item_estoque_id)];
          if (p) {
            if (p.quantidade <= 0) alerta = '<div class="alerta-estoque red">Sem estoque no momento</div>';
            else if (Number(it.quantidade) > p.quantidade) alerta = `<div class="alerta-estoque red">Só há ${p.quantidade} un. em estoque</div>`;
            else if (p.quantidade <= p.minimo) alerta = `<div class="alerta-estoque">Estoque baixo: ${p.quantidade} un. (mín. ${p.minimo})</div>`;
          }
        }
        const desc = it.tipo === 'avulso'
          ? `<input class="input" style="height:36px" data-k="descricao" value="${esc(it.descricao)}" placeholder="Descrição do item">`
          : `<span>${esc(it.descricao)}</span>`;
        row.innerHTML = `
          <div><span class="tag ${it.tipo}">${tagTxt}</span> ${desc}${alerta}</div>
          <input class="input qty-input" data-k="quantidade" type="number" min="1" step="${it.tipo === 'peca' ? 1 : 'any'}" value="${it.quantidade}">
          <input class="input money-input vu" data-k="valor_unitario" inputmode="decimal" value="${String(Number(it.valor_unitario).toFixed(2)).replace('.', ',')}">
          <div class="st">${brl(it.quantidade * it.valor_unitario)}</div>
          <button type="button" class="x-btn" title="Remover">×</button>`;
        $$('input', row).forEach((inp) => inp.addEventListener('change', () => {
          const k = inp.dataset.k;
          it[k] = k === 'descricao' ? inp.value : (k === 'valor_unitario' ? parseValor(inp.value) : Number(inp.value) || 1);
          render();
        }));
        $('.x-btn', row).addEventListener('click', () => { itens.splice(idx, 1); render(); });
        corpo.appendChild(row);
      });
      vazio.hidden = itens.length > 0;
      $('#orc-qtd').textContent = itens.length + (itens.length === 1 ? ' item' : ' itens');
      const subtotal = itens.reduce((s, i) => s + i.quantidade * i.valor_unitario, 0);
      const desc = parseValor(desconto.value);
      $('#sum-subtotal').textContent = brl(subtotal);
      $('#sum-total').textContent = brl(Math.max(subtotal - desc, 0));
      $('#desc-erro').hidden = desc <= subtotal;
      hidden.value = JSON.stringify(itens);
    };
    const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

    $('#add-servico').addEventListener('change', (e) => {
      const s = servicos[e.target.value]; e.target.value = '';
      if (s) { itens.push({ tipo: 'servico', descricao: s.descricao, quantidade: 1, valor_unitario: s.preco }); render(); }
    });
    $('#add-peca').addEventListener('change', (e) => {
      const p = pecas[e.target.value]; e.target.value = '';
      if (!p) return;
      const ja = itens.find((i) => i.tipo === 'peca' && String(i.item_estoque_id) === String(p.id));
      if (ja) ja.quantidade += 1;
      else itens.push({ tipo: 'peca', item_estoque_id: p.id, descricao: p.descricao, quantidade: 1, valor_unitario: p.preco });
      render();
    });
    $('#add-avulso').addEventListener('click', () => { itens.push({ tipo: 'avulso', descricao: '', quantidade: 1, valor_unitario: 0 }); render(); });
    desconto.addEventListener('input', render);

    const validade = $('#validade_dias'), validoAte = $('#valido-ate');
    const atualizaValidade = () => {
      const d = new Date(); d.setDate(d.getDate() + Number(validade.value));
      validoAte.textContent = 'Válido até ' + d.toLocaleDateString('pt-BR');
    };
    if (validade) { validade.addEventListener('change', atualizaValidade); atualizaValidade(); }

    // equipamentos do cliente selecionado (RF-10)
    const cli = $('#cliente_id'), eq = $('#equipamento_id');
    const atualizaEquip = () => {
      const lista = dados.equipamentos[cli.value] || [];
      const atual = eq.dataset.atual || '';
      eq.innerHTML = '<option value="">Nenhum / não se aplica</option>' + lista.map((x) =>
        `<option value="${x.id}" ${String(x.id) === atual ? 'selected' : ''}>${esc(x.nome)}</option>`).join('');
    };
    if (cli && eq) { cli.addEventListener('change', () => { eq.dataset.atual = ''; atualizaEquip(); }); atualizaEquip(); }

    render();
  }

  /* ---------- nova OS: equipamentos do cliente */
  const osCli = $('#os-cliente');
  if (osCli) {
    const dados = JSON.parse($('#os-dados').textContent);
    const sel = $('#os-equip');
    const f = osCli.form;
    const atualiza = () => {
      const lista = dados[osCli.value] || [];
      sel.innerHTML = '<option value="">+ Novo equipamento (preencher abaixo)</option>' +
        lista.map((x) => `<option value="${x.id}">${x.nome}</option>`).join('');
    };
    sel.addEventListener('change', () => {
      const lista = dados[osCli.value] || [];
      const x = lista.find((e) => String(e.id) === sel.value);
      ['equip_tipo', 'equip_modelo', 'equip_serie'].forEach((k, i) => {
        f.elements[k].value = x ? [x.tipo, x.modelo, x.serie][i] || '' : '';
      });
    });
    osCli.addEventListener('change', atualiza);
    atualiza();
  }

  /* ---------- movimentação de estoque: texto de ajuda por tipo */
  const movTipos = $$('input[name="tipo_mov"]');
  if (movTipos.length) {
    const ajuda = { entrada: 'Soma ao saldo atual.', saida: 'Subtrai do saldo atual.', ajuste: 'Define o novo saldo após a contagem do inventário.' };
    const ph = { entrada: 'Ex.: NF 4590 · Kingston', saida: 'Ex.: Venda balcão, perda, garantia', ajuste: 'Ex.: Inventário mensal' };
    const upd = () => {
      const v = movTipos.find((r) => r.checked).value;
      $('#mov-ajuda').textContent = ajuda[v];
      $('#mov-ref').placeholder = ph[v];
    };
    movTipos.forEach((r) => r.addEventListener('change', upd)); upd();
  }
})();
