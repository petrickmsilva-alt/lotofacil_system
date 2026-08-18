/* ============================================================
   CONFERENCIA.JS - ES5 puro
   ============================================================ */

/* Valores fixos oficiais */
var PREMIO = {};
PREMIO[11] = 7.00;
PREMIO[12] = 14.00;
PREMIO[13] = 35.00;
PREMIO[14] = 0;
PREMIO[15] = 0;

/* Concurso em edição no modal */
var concursoAtual = 0;

/* ── Init ──────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {

    /* Conferir por número */
    document.getElementById('btn-conferir-numero').onclick = function () {
        var inp = document.getElementById('input-concurso');
        var num = parseInt(inp.value, 10);
        if (!num || num < 1) { alert('Digite o concurso.'); return; }
        conferirConcurso(num);
    };

    /* Conferir todas */
    document.getElementById('btn-conferir-todas').onclick = conferirTodas;

    /* Fechar painel */
    document.getElementById('btn-fechar-painel').onclick = fecharPainel;

    /* Fechar modal principal */
    document.getElementById('btn-fechar-modal').onclick = fecharModal;
    document.getElementById('modal-bg').onclick         = fecharModal;

    /* Fechar modal confirmação */
    document.getElementById('btn-fechar-confirmar').onclick = fecharConfirmar;
    document.getElementById('confirmar-bg').onclick         = fecharConfirmar;
    document.getElementById('btn-confirmar-nao').onclick    = fecharConfirmar;

    /* ESC fecha modais */
    document.onkeydown = function (e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            fecharModal();
            fecharConfirmar();
        }
    };

    /* Botões da tabela */
    vincularBotoesTabela();
});

function vincularBotoesTabela() {
    var btnsVer  = document.querySelectorAll('.btn-ver');
    var btnsConf = document.querySelectorAll('.btn-conf');
    var btnsAdd  = document.querySelectorAll('.btn-add');
    var btnsDel  = document.querySelectorAll('.btn-del');
    var i = 0;

    for (i = 0; i < btnsVer.length; i++) {
        btnsVer[i].onclick = function () {
            abrirModalCartelas(parseInt(this.getAttribute('data-concurso'), 10));
        };
    }
    for (i = 0; i < btnsConf.length; i++) {
        btnsConf[i].onclick = function () {
            conferirConcurso(parseInt(this.getAttribute('data-concurso'), 10));
        };
    }
    for (i = 0; i < btnsAdd.length; i++) {
        btnsAdd[i].onclick = function () {
            abrirModalAdicionar(parseInt(this.getAttribute('data-concurso'), 10));
        };
    }
    for (i = 0; i < btnsDel.length; i++) {
        btnsDel[i].onclick = function () {
            pedirConfirmacaoApagar(parseInt(this.getAttribute('data-concurso'), 10));
        };
    }
}

/* ── Fechar modais ─────────────────────────────────────────── */
function fecharModal() {
    document.getElementById('modal-principal').style.display = 'none';
}

function fecharConfirmar() {
    document.getElementById('modal-confirmar').style.display = 'none';
}

function fecharPainel() {
    document.getElementById('painel-resultado').className =
        'section painel-escondido';
}

/* =========================================================
   MODAL PRINCIPAL — VER CARTELAS
   ========================================================= */
function abrirModalCartelas(concurso) {
    concursoAtual = concurso;

    var modal  = document.getElementById('modal-principal');
    var titulo = document.getElementById('modal-titulo');
    var corpo  = document.getElementById('modal-corpo');
    var abas   = document.getElementById('modal-abas');
    var footer = document.getElementById('modal-footer');

    modal.style.display = 'flex';
    titulo.textContent  = 'Cartelas — Concurso ' + concurso;
    corpo.innerHTML     = '<p>Carregando...</p>';
    abas.innerHTML      = '';
    footer.innerHTML    = '';

    /* Rodapé com ações */
    footer.innerHTML =
        '<button class="btn btn-success btn-sm" ' +
        'id="footer-btn-add">' +
        '<i class="fas fa-plus"></i> Adicionar Cartelas</button>' +
        '<button class="btn btn-outline btn-sm" ' +
        'id="footer-btn-conf">' +
        '<i class="fas fa-check"></i> Conferir Este Concurso</button>' +
        '<button class="btn btn-danger btn-sm" ' +
        'id="footer-btn-del">' +
        '<i class="fas fa-trash"></i> Apagar Todas</button>';

    document.getElementById('footer-btn-add').onclick = function () {
        fecharModal();
        abrirModalAdicionar(concursoAtual);
    };
    document.getElementById('footer-btn-conf').onclick = function () {
        fecharModal();
        conferirConcurso(concursoAtual);
    };
    document.getElementById('footer-btn-del').onclick = function () {
        fecharModal();
        pedirConfirmacaoApagar(concursoAtual);
    };

    carregarCartelas(concurso);
}

function carregarCartelas(concurso) {
    var corpo = document.getElementById('modal-corpo');
    corpo.innerHTML = '<p>Carregando...</p>';

    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/cartelas_concurso/' + concurso, true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        if (xhr.status === 200) {
            var data = null;
            try { data = JSON.parse(xhr.responseText); } catch (e) { return; }
            corpo.innerHTML = montarListaCartelas(
                data.cartelas || [], concurso
            );
            vincularBotoesCartela(concurso);
        } else {
            corpo.innerHTML = '<p>Erro ao carregar.</p>';
        }
    };
    xhr.send();
}

function montarListaCartelas(cartelas, concurso) {
    var html = '';
    var i, j;

    if (cartelas.length === 0) {
        return '<p style="color:var(--text-muted);">' +
               'Sem cartelas para o concurso ' + concurso + '</p>';
    }

    /* Barra de seleção */
    html += '<div class="barra-sel">';
    html += '<label>' +
            '<input type="checkbox" id="chk-todos"> ' +
            'Selecionar todos</label>';
    html += '<button class="btn btn-danger btn-sm" ' +
            'id="btn-apagar-selecionados">' +
            '<i class="fas fa-trash"></i> Apagar Selecionados</button>';
    html += '</div>';

    /* Lista */
    html += '<div id="lista-cartelas">';

    for (i = 0; i < cartelas.length; i++) {
        var c   = cartelas[i];
        var dez = c.dezenas || [];
        var ac  = parseInt(c.acertos || 0, 10);

        var borda = '1px solid rgba(108,92,231,0.2)';
        if (ac >= 15)      { borda = '2px solid #FF6B6B'; }
        else if (ac >= 14) { borda = '2px solid var(--primary)'; }
        else if (ac >= 13) { borda = '2px solid var(--success)'; }
        else if (ac >= 12) { borda = '2px solid var(--warning)'; }
        else if (ac >= 11) { borda = '2px solid var(--info)'; }

        html += '<div class="cartela-item" ' +
                'style="border:' + borda + ';" ' +
                'data-id="' + c.id + '">';

        /* Checkbox + cabeçalho */
        html += '<div class="cartela-item-header">';
        html += '<label class="chk-label">' +
                '<input type="checkbox" class="chk-cartela" ' +
                'data-id="' + c.id + '"> ' +
                '#' + c.id + '</label>';

        if (c.conferida) {
            if (ac >= 11) {
                var prem = parseFloat(c.premio || 0);
                html += '<span class="badge badge-premio_' + ac + '">' +
                        ac + ' pts — R$ ' + prem.toFixed(2) + '</span>';
            } else {
                html += '<span class="badge badge-sem_premio">' +
                        ac + ' pts</span>';
            }
        } else {
            html += '<span class="badge badge-warning">Pendente</span>';
        }

        html += '<button class="btn btn-sm btn-danger btn-del-cartela" ' +
                'data-id="' + c.id + '" data-concurso="' + concurso + '">' +
                '<i class="fas fa-times"></i></button>';
        html += '</div>';

        /* Bolas */
        html += '<div class="bolas-cartela">';
        for (j = 0; j < dez.length; j++) {
            var dn  = parseInt(dez[j], 10);
            var pad = dn < 10 ? '0' : '';
            html += '<span class="bola-mini">' + pad + dn + '</span>';
        }
        html += '</div>';

        /* Score */
        html += '<div class="cartela-score">Score: ' +
                parseFloat(c.score_total || 0).toFixed(4) + '</div>';

        html += '</div>';
    }

    html += '</div>';
    return html;
}

function vincularBotoesCartela(concurso) {
    /* Selecionar todos */
    var chkTodos = document.getElementById('chk-todos');
    if (chkTodos) {
        chkTodos.onchange = function () {
            var chks = document.querySelectorAll('.chk-cartela');
            var k = 0;
            while (k < chks.length) {
                chks[k].checked = chkTodos.checked;
                k = k + 1;
            }
        };
    }

    /* Apagar selecionados */
    var btnApagarSel = document.getElementById('btn-apagar-selecionados');
    if (btnApagarSel) {
        btnApagarSel.onclick = function () {
            var selecionados = [];
            var chks = document.querySelectorAll('.chk-cartela:checked');
            var k = 0;
            while (k < chks.length) {
                selecionados.push(parseInt(
                    chks[k].getAttribute('data-id'), 10
                ));
                k = k + 1;
            }
            if (selecionados.length === 0) {
                alert('Selecione ao menos uma cartela.');
                return;
            }
            if (confirm('Apagar ' + selecionados.length +
                        ' cartela(s) selecionada(s)?')) {
                apagarCartelas(selecionados, concurso);
            }
        };
    }

    /* Apagar cartela individual */
    var btnsDelInd = document.querySelectorAll('.btn-del-cartela');
    var i = 0;
    while (i < btnsDelInd.length) {
        btnsDelInd[i].onclick = function () {
            var cid  = parseInt(this.getAttribute('data-id'), 10);
            var conc = parseInt(this.getAttribute('data-concurso'), 10);
            if (confirm('Apagar cartela #' + cid + '?')) {
                apagarCartelas([cid], conc);
            }
        };
        i = i + 1;
    }
}

/* =========================================================
   APAGAR CARTELAS
   ========================================================= */
function pedirConfirmacaoApagar(concurso) {
    var modal  = document.getElementById('modal-confirmar');
    var texto  = document.getElementById('texto-confirmar');
    var btnSim = document.getElementById('btn-confirmar-sim');

    modal.style.display = 'flex';
    texto.innerHTML =
        '<i class="fas fa-exclamation-triangle" ' +
        'style="color:var(--danger);font-size:24px;"></i><br><br>' +
        'Tem certeza que deseja apagar <strong>TODAS</strong> as cartelas ' +
        'do concurso <strong>' + concurso + '</strong>?<br>' +
        '<small style="color:var(--text-muted);">' +
        'Esta ação não pode ser desfeita.</small>';

    btnSim.onclick = function () {
        fecharConfirmar();
        apagarTodasConcurso(concurso);
    };
}

function apagarTodasConcurso(concurso) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/apagar_cartelas_concurso', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        if (xhr.status === 200) {
            var data = JSON.parse(xhr.responseText);
            if (data.status === 'ok') {
                /* Remover linha da tabela */
                var row = document.getElementById('row-' + concurso);
                if (row) { row.parentNode.removeChild(row); }
                mostrarNotificacao(
                    data.apagadas + ' cartelas apagadas.', 'success'
                );
            } else {
                mostrarNotificacao('Erro: ' + data.msg, 'danger');
            }
        }
    };
    xhr.send(JSON.stringify({ concurso: concurso }));
}

function apagarCartelas(ids, concurso) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/apagar_cartelas', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        if (xhr.status === 200) {
            var data = JSON.parse(xhr.responseText);
            if (data.status === 'ok') {
                mostrarNotificacao(
                    data.apagadas + ' cartela(s) apagada(s).', 'success'
                );
                /* Recarregar lista */
                carregarCartelas(concurso);
            } else {
                mostrarNotificacao('Erro: ' + data.msg, 'danger');
            }
        }
    };
    xhr.send(JSON.stringify({ ids: ids }));
}

/* =========================================================
   ADICIONAR CARTELAS
   ========================================================= */
function abrirModalAdicionar(concurso) {
    concursoAtual = concurso;

    var modal  = document.getElementById('modal-principal');
    var titulo = document.getElementById('modal-titulo');
    var corpo  = document.getElementById('modal-corpo');
    var abas   = document.getElementById('modal-abas');
    var footer = document.getElementById('modal-footer');

    modal.style.display = 'flex';
    titulo.textContent  = 'Adicionar Cartelas — Concurso ' + concurso;
    abas.innerHTML      = '';
    footer.innerHTML    = '';

    corpo.innerHTML =
        '<div class="form-adicionar">' +
        '<div class="form-group">' +
        '<label>Quantidade de cartelas a adicionar:</label>' +
        '<input type="number" id="qtd-adicionar" ' +
        'class="form-control" value="5" min="1" max="50" ' +
        'style="max-width:120px;">' +
        '</div>' +
        '<div class="form-group" style="margin-top:12px;">' +
        '<label>Custo estimado:</label>' +
        '<span id="custo-add" style="font-size:20px;font-weight:700;' +
        'color:var(--warning);">R$ 17,50</span>' +
        '</div>' +
        '<button id="btn-gerar-add" class="btn btn-primary btn-lg" ' +
        'style="margin-top:16px;">' +
        '<i class="fas fa-magic"></i> Gerar e Adicionar</button>' +
        '<div id="add-resultado" style="margin-top:16px;"></div>' +
        '</div>';

    /* Atualizar custo */
    document.getElementById('qtd-adicionar').oninput = function () {
        var qtd  = parseInt(this.value, 10) || 0;
        var custo = (qtd * 3.50).toFixed(2);
        document.getElementById('custo-add').textContent = 'R$ ' + custo;
    };

    /* Gerar e adicionar */
    document.getElementById('btn-gerar-add').onclick = function () {
        var qtd = parseInt(
            document.getElementById('qtd-adicionar').value, 10
        );
        if (!qtd || qtd < 1) { alert('Informe a quantidade.'); return; }
        gerarAdicionarCartelas(concurso, qtd);
    };
}

function gerarAdicionarCartelas(concurso, qtd) {
    var resDiv = document.getElementById('add-resultado');
    var btnGen = document.getElementById('btn-gerar-add');

    resDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> ' +
                       'Gerando ' + qtd + ' cartelas...</p>';
    btnGen.disabled  = true;

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/adicionar_cartelas_concurso', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        btnGen.disabled = false;
        if (xhr.status === 200) {
            var data = null;
            try { data = JSON.parse(xhr.responseText); } catch (e) { return; }
            if (data.status === 'ok') {
                resDiv.innerHTML =
                    '<div class="alert alert-success">' +
                    '<i class="fas fa-check"></i> ' +
                    data.adicionadas + ' cartelas adicionadas! ' +
                    'Custo: R$ ' +
                    (data.adicionadas * 3.50).toFixed(2) +
                    '</div>' +
                    '<button class="btn btn-outline btn-sm" ' +
                    'onclick="abrirModalCartelas(' + concurso + ')">' +
                    'Ver cartelas</button>';
            } else {
                resDiv.innerHTML =
                    '<div class="alert alert-danger">' +
                    (data.msg || 'Erro ao gerar.') + '</div>';
            }
        } else {
            resDiv.innerHTML =
                '<div class="alert alert-danger">Erro HTTP: ' +
                xhr.status + '</div>';
        }
    };
    xhr.send(JSON.stringify({ concurso: concurso, quantidade: qtd }));
}

/* =========================================================
   CONFERIR CONCURSO
   ========================================================= */
function conferirConcurso(concurso) {
    var painel   = document.getElementById('painel-resultado');
    var titulo   = document.getElementById('titulo-resultado');
    var conteudo = document.getElementById('conteudo-resultado');

    painel.className   = 'section painel-visivel';
    titulo.textContent = 'Conferindo concurso ' + concurso + '...';
    conteudo.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> ' +
                         'Buscando resultado da Caixa...</p>';
    painel.scrollIntoView();

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/conferir_concurso', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        if (xhr.status === 200) {
            var data = null;
            try { data = JSON.parse(xhr.responseText); } catch (e) { return; }
            titulo.textContent = 'Concurso ' + concurso +
                ' — ' + (data.total_cartelas || 0) + ' cartelas';
            conteudo.innerHTML = montarResultado(data);
        } else {
            conteudo.innerHTML =
                '<p class="alert alert-danger">Erro HTTP: ' +
                xhr.status + '</p>';
        }
    };
    xhr.send(JSON.stringify({ concurso: concurso }));
}

function montarResultado(data) {
    var html = '';
    var i, j;

    if (data.status === 'erro' || data.status === 'vazio') {
        return '<p class="alert alert-danger">' +
               (data.msg || 'Sem dados.') + '</p>';
    }

    /* Resultado sorteado */
    var dez = data.resultado || [];
    html += '<div style="margin-bottom:16px;">';
    html += '<strong>Resultado sorteado:</strong>';
    html += '<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:5px;">';
    for (i = 0; i < dez.length; i++) {
        var n   = parseInt(dez[i], 10);
        var pad = n < 10 ? '0' : '';
        html += '<span class="bola-mini selecionada">' + pad + n + '</span>';
    }
    html += '</div></div>';

    /* Prêmios */
    var pof     = data.premios_oficiais || {};
    var faixas  = [11, 12, 13, 14, 15];
    var clsMap  = {11:'a11', 12:'a12', 13:'a13', 14:'a14', 15:'a15'};
    html += '<div class="premios-conf-grid" style="margin-bottom:16px;">';
    for (i = 0; i < faixas.length; i++) {
        var fx   = faixas[i];
        var val  = parseFloat(pof[fx] || 0);
        var tipo = fx <= 13 ? 'Fixo' : 'Rateio';
        var vs   = val > 0 ? 'R$ ' + val.toFixed(2) : 'Rateio';
        html += '<div class="acerto-card ' + (clsMap[fx] || '') + '">';
        html += '<span class="acerto-num">' + fx + ' pts</span>';
        html += '<span class="acerto-label">' + vs + '</span>';
        html += '<span class="acerto-premio">' + tipo + '</span>';
        html += '</div>';
    }
    html += '</div>';

    /* Resumo */
    html += '<div class="conf-resumo">';
    html += '<span><strong>' + (data.total_cartelas  || 0) +
            '</strong> cartelas</span>';
    html += '<span><strong style="color:var(--success);">' +
            (data.total_premiadas || 0) + '</strong> premiadas</span>';
    html += '</div>';

    /* Cartelas */
    var cartelas = data.cartelas || [];
    html += '<h3 style="margin:16px 0 10px;">Detalhes por Cartela:</h3>';

    for (i = 0; i < cartelas.length; i++) {
        var c      = cartelas[i];
        var acert  = parseInt(c.acertos || 0, 10);
        var premio = parseFloat(c.premio || 0);
        var fundo  = 'var(--dark-3)';
        if (acert >= 15)      { fundo = 'rgba(225,112,85,0.2)'; }
        else if (acert >= 14) { fundo = 'rgba(108,92,231,0.2)'; }
        else if (acert >= 13) { fundo = 'rgba(0,184,148,0.2)'; }
        else if (acert >= 12) { fundo = 'rgba(253,203,110,0.15)'; }
        else if (acert >= 11) { fundo = 'rgba(116,185,255,0.15)'; }

        html += '<div class="cartela-conf" style="background:' + fundo + ';">';
        html += '<div class="cartela-conf-header">';
        html += '<strong>Cartela #' + (c.cartela_id || i + 1) + '</strong>';
        html += '<span class="badge badge-' + (c.status || 'sem_premio') +
                '">' + acert + ' pontos</span>';
        if (premio > 0) {
            html += '<span style="color:var(--success);font-weight:700;">' +
                    'R$ ' + premio.toFixed(2) + '</span>';
        }
        html += '</div>';

        /* Bolas */
        var dezC  = c.dezenas_cartela   || [];
        var acertL = c.dezenas_acertadas || [];
        var setA  = {};
        for (j = 0; j < acertL.length; j++) { setA[acertL[j]] = true; }

        html += '<div style="display:flex;flex-wrap:wrap;gap:4px;margin:8px 0;">';
        for (j = 0; j < dezC.length; j++) {
            var dn   = parseInt(dezC[j], 10);
            var pad2 = dn < 10 ? '0' : '';
            var cls2 = setA[dn] ? 'bola-mini selecionada' : 'bola-mini';
            html += '<span class="' + cls2 + '">' + pad2 + dn + '</span>';
        }
        html += '</div>';

        html += '<div style="font-size:12px;color:var(--text-muted);">';
        html += 'Acertadas: ';
        for (j = 0; j < acertL.length; j++) {
            var an  = parseInt(acertL[j], 10);
            var ap  = an < 10 ? '0' : '';
            html += '<strong style="color:var(--success);">' +
                    ap + an + ' </strong>';
        }
        html += '</div>';
        html += '</div>';
    }

    return html;
}

/* =========================================================
   CONFERIR TODAS PENDENTES
   ========================================================= */
function conferirTodas() {
    var painel   = document.getElementById('painel-resultado');
    var titulo   = document.getElementById('titulo-resultado');
    var conteudo = document.getElementById('conteudo-resultado');

    painel.className   = 'section painel-visivel';
    titulo.textContent = 'Conferindo pendentes...';
    conteudo.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> ' +
                         'Aguarde...</p>';
    painel.scrollIntoView();

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/conferir', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        if (xhr.status === 200) {
            var data = JSON.parse(xhr.responseText);
            titulo.textContent = 'Conferência Concluída';
            conteudo.innerHTML =
                '<p class="alert alert-success">' +
                (data.conferidas || 0) + ' cartelas conferidas!</p>';
            setTimeout(function () { location.reload(); }, 2000);
        } else {
            conteudo.innerHTML =
                '<p class="alert alert-danger">Erro HTTP: ' +
                xhr.status + '</p>';
        }
    };
    xhr.send();
}

/* =========================================================
   NOTIFICAÇÃO FLUTUANTE
   ========================================================= */
function mostrarNotificacao(msg, tipo) {
    var div = document.createElement('div');
    div.className = 'notificacao notif-' + (tipo || 'success');
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(function () {
        if (div.parentNode) { div.parentNode.removeChild(div); }
    }, 3000);
}