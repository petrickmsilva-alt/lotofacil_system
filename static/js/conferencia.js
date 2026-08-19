/* ============================================================
   CONFERENCIA.JS — v2.0 ROBUSTA
   Todas as verificações de null incluídas
   ============================================================ */

console.log('[CONFERENCIA] JS v2.0 carregado');


document.addEventListener('DOMContentLoaded', function () {
    console.log('[CONFERENCIA] DOM pronto, inicializando...');

    /* Botão fechar modal */
    var btnFechar = document.getElementById('btn-fechar-modal');
    if (btnFechar) {
        btnFechar.addEventListener('click', fecharModal);
    }

    /* Fundo do modal */
    var modalBg = document.getElementById('modal-lote-bg');
    if (modalBg) {
        modalBg.addEventListener('click', fecharModal);
    }

    /* Fechar painel resultado */
    var btnFecharP = document.getElementById('btn-fechar-painel');
    if (btnFecharP) {
        btnFecharP.addEventListener('click', fecharPainel);
    }

    /* Conferir todos */
    var btnTodos = document.getElementById('btn-conferir-todos');
    if (btnTodos) {
        btnTodos.addEventListener('click', conferirTodos);
    }

    /* Conferir por número */
    var btnNum = document.getElementById('btn-conferir-num');
    if (btnNum) {
        btnNum.addEventListener('click', function () {
            var inp = document.getElementById('input-concurso');
            if (!inp) { return; }
            var num = parseInt(inp.value, 10);
            if (!num || num < 1) {
                alert('Digite o número do concurso.');
                return;
            }
            conferirConcursoNumero(num);
        });
    }

    /* Botões dos lotes (via delegação de eventos — funciona sempre) */
    document.addEventListener('click', function (e) {
        var target = e.target;

        /* Subir na árvore até achar o botão (caso clique no ícone) */
        while (target && target !== document) {
            if (target.classList && target.classList.contains('btn-ver-lote')) {
                e.preventDefault();
                var lote = target.getAttribute('data-lote');
                console.log('[CLICK] Ver lote:', lote);
                verCartelasLote(lote);
                return;
            }
            if (target.classList && target.classList.contains('btn-conferir-lote')) {
                e.preventDefault();
                var lote2 = target.getAttribute('data-lote');
                var conc  = target.getAttribute('data-concurso');
                console.log('[CLICK] Conferir lote:', lote2, 'concurso:', conc);
                conferirLote(lote2, conc);
                return;
            }
            if (target.classList && target.classList.contains('btn-apagar-lote')) {
                e.preventDefault();
                var lote3 = target.getAttribute('data-lote');
                console.log('[CLICK] Apagar lote:', lote3);
                apagarLote(lote3);
                return;
            }
            target = target.parentNode;
        }
    });

    /* ESC fecha modal */
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            fecharModal();
        }
    });

    console.log('[CONFERENCIA] Inicialização completa');
});


/* ============================================================
   FECHAR MODAIS
   ============================================================ */
function fecharModal() {
    var m = document.getElementById('modal-lote');
    if (m) { m.style.display = 'none'; }
}

function fecharPainel() {
    var p = document.getElementById('painel-resultado');
    if (p) { p.className = 'section painel-escondido'; }
}


/* ============================================================
   VER CARTELAS DO LOTE
   ============================================================ */
function verCartelasLote(lote_id) {
    if (!lote_id) {
        alert('Lote inválido.');
        return;
    }

    console.log('[verCartelasLote] Iniciando:', lote_id);

    var modal  = document.getElementById('modal-lote');
    var titulo = document.getElementById('modal-lote-titulo');
    var corpo  = document.getElementById('modal-lote-corpo');

    if (!modal || !titulo || !corpo) {
        console.error('[verCartelasLote] Modal não encontrado');
        alert('Erro: modal não existe no HTML.');
        return;
    }

    modal.style.display = 'flex';
    titulo.textContent  = 'Cartelas do Lote';
    corpo.innerHTML     = '<p>Carregando cartelas...</p>';

    fetch('/api/lote/' + encodeURIComponent(lote_id))
        .then(function (r) {
            console.log('[verCartelasLote] Status:', r.status);
            if (!r.ok) {
                throw new Error('HTTP ' + r.status);
            }
            return r.json();
        })
        .then(function (data) {
            console.log('[verCartelasLote] Dados:', data);
            corpo.innerHTML = montarCartelas(data.cartelas || []);
        })
        .catch(function (err) {
            console.error('[verCartelasLote] Erro:', err);
            corpo.innerHTML = '<p class="alert alert-danger">Erro: ' +
                              String(err) + '</p>';
        });
}


function montarCartelas(cartelas) {
    if (!cartelas || cartelas.length === 0) {
        return '<p style="color:#888;">Nenhuma cartela encontrada.</p>';
    }

    var html = '<p style="color:#888;margin-bottom:16px;">' +
               cartelas.length + ' cartela(s) neste lote</p>';

    for (var i = 0; i < cartelas.length; i++) {
        var c   = cartelas[i];
        var dez = c.dezenas || [];
        var ac  = parseInt(c.acertos || 0, 10);

        var borda = '1px solid rgba(108,92,231,0.2)';
        if      (ac >= 15) { borda = '2px solid #FF6B6B'; }
        else if (ac >= 14) { borda = '2px solid #6C5CE7'; }
        else if (ac >= 13) { borda = '2px solid #00B894'; }
        else if (ac >= 11) { borda = '2px solid #FDCB6E'; }

        html += '<div class="cartela-mini" style="border:' + borda + ';">';
        html += '<div style="display:flex;justify-content:space-between;' +
                'margin-bottom:8px;">';
        html += '<strong>Cartela #' + c.id + '</strong>';

        if (c.conferida) {
            if (ac >= 11) {
                html += '<span style="color:#00B894;">' +
                        ac + ' pts — R$ ' +
                        parseFloat(c.premio || 0).toFixed(2) + '</span>';
            } else {
                html += '<span style="color:#888;">' + ac + ' pts</span>';
            }
        } else {
            html += '<span class="badge badge-warning">Pendente</span>';
        }
        html += '</div>';

        html += '<div style="display:flex;flex-wrap:wrap;gap:4px;">';
        for (var j = 0; j < dez.length; j++) {
            var dn  = parseInt(dez[j], 10);
            var pad = dn < 10 ? '0' : '';
            html += '<span class="bola-mini">' + pad + dn + '</span>';
        }
        html += '</div>';

        html += '<div style="font-size:11px;color:#888;margin-top:6px;">' +
                'Score: ' + parseFloat(c.score_total || 0).toFixed(4) +
                '</div>';
        html += '</div>';
    }
    return html;
}


/* ============================================================
   CONFERIR LOTE
   ============================================================ */
function conferirLote(lote_id, concurso) {
    if (!lote_id) { return; }

    console.log('[conferirLote] Lote:', lote_id, 'Concurso:', concurso);

    var painel   = document.getElementById('painel-resultado');
    var titulo   = document.getElementById('titulo-resultado');
    var conteudo = document.getElementById('conteudo-resultado');

    if (painel)   { painel.className = 'section painel-visivel'; }
    if (titulo)   {
        titulo.textContent = 'Conferindo lote — Concurso ' + concurso + '...';
    }
    if (conteudo) {
        conteudo.innerHTML = '<p>Buscando resultado da Caixa...</p>';
    }
    if (painel)   { painel.scrollIntoView({behavior: 'smooth'}); }

    fetch('/api/conferir_lote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lote_id: lote_id })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        console.log('[conferirLote] Resposta:', data);
        if (data.status === 'ok') {
            if (titulo) {
                titulo.textContent = 'Concurso ' + data.concurso +
                                     ' — Conferido';
            }
            if (conteudo) {
                conteudo.innerHTML = montarResultado(data);
            }
            setTimeout(function () { location.reload(); }, 4000);
        } else {
            if (conteudo) {
                conteudo.innerHTML = '<p class="alert alert-danger">' +
                                     (data.msg || 'Erro') + '</p>';
            }
        }
    })
    .catch(function (err) {
        console.error('[conferirLote] Erro:', err);
        if (conteudo) {
            conteudo.innerHTML = '<p class="alert alert-danger">Erro: ' +
                                 String(err) + '</p>';
        }
    });
}


/* ============================================================
   CONFERIR NÚMERO
   ============================================================ */
function conferirConcursoNumero(concurso) {
    console.log('[conferirConcursoNumero]', concurso);

    var painel   = document.getElementById('painel-resultado');
    var titulo   = document.getElementById('titulo-resultado');
    var conteudo = document.getElementById('conteudo-resultado');

    if (painel)   { painel.className = 'section painel-visivel'; }
    if (titulo)   {
        titulo.textContent = 'Conferindo concurso ' + concurso + '...';
    }
    if (conteudo) {
        conteudo.innerHTML = '<p>Buscando resultado da Caixa...</p>';
    }
    if (painel)   { painel.scrollIntoView({behavior: 'smooth'}); }

    fetch('/api/conferir_concurso', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ concurso: concurso })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        console.log('[conferirConcursoNumero] Resposta:', data);
        if (titulo) {
            titulo.textContent = 'Concurso ' + concurso + ' — ' +
                                 (data.total_cartelas || 0) + ' cartelas';
        }
        if (conteudo) {
            conteudo.innerHTML = montarResultado(data);
        }
    })
    .catch(function (err) {
        console.error('[conferirConcursoNumero] Erro:', err);
        if (conteudo) {
            conteudo.innerHTML = '<p class="alert alert-danger">Erro: ' +
                                 String(err) + '</p>';
        }
    });
}


function montarResultado(data) {
    if (data.status === 'erro' || data.status === 'vazio') {
        return '<p class="alert alert-danger">' +
               (data.msg || 'Sem dados.') + '</p>';
    }

    var html = '';
    var i, j;
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

    html += '<div class="conf-resumo">';
    html += '<span><strong>' + (data.total_cartelas || 0) +
            '</strong> cartelas</span>';
    html += '<span><strong style="color:#00B894;">' +
            (data.total_premiadas || 0) + '</strong> premiadas</span>';
    html += '</div>';

    var cartelas = data.cartelas || [];
    if (cartelas.length > 0) {
        html += '<h3 style="margin:16px 0 10px;">Detalhes das cartelas:</h3>';

        for (i = 0; i < cartelas.length; i++) {
            var c    = cartelas[i];
            var acs  = parseInt(c.acertos || 0, 10);
            var prem = parseFloat(c.premio || 0);

            var fundo = '#2d2d5e';
            if      (acs >= 15) { fundo = 'rgba(225,112,85,0.2)'; }
            else if (acs >= 14) { fundo = 'rgba(108,92,231,0.2)'; }
            else if (acs >= 13) { fundo = 'rgba(0,184,148,0.2)'; }
            else if (acs >= 12) { fundo = 'rgba(253,203,110,0.15)'; }
            else if (acs >= 11) { fundo = 'rgba(116,185,255,0.15)'; }

            html += '<div class="cartela-conf" style="background:' +
                    fundo + ';">';
            html += '<div class="cartela-conf-header">';
            html += '<strong>Cartela #' + (c.cartela_id || i + 1) + '</strong>';
            html += '<span class="badge badge-' +
                    (c.status || 'sem_premio') + '">' +
                    acs + ' pontos</span>';
            if (prem > 0) {
                html += '<span style="color:#00B894;font-weight:700;">R$ ' +
                        prem.toFixed(2) + '</span>';
            }
            html += '</div>';

            var dezC  = c.dezenas_cartela   || [];
            var acert = c.dezenas_acertadas || [];
            var setA  = {};
            for (j = 0; j < acert.length; j++) { setA[acert[j]] = true; }

            html += '<div style="display:flex;flex-wrap:wrap;gap:4px;' +
                    'margin:8px 0;">';
            for (j = 0; j < dezC.length; j++) {
                var dn = parseInt(dezC[j], 10);
                var p2 = dn < 10 ? '0' : '';
                var cl = setA[dn] ? 'bola-mini selecionada' : 'bola-mini';
                html += '<span class="' + cl + '">' + p2 + dn + '</span>';
            }
            html += '</div>';
            html += '</div>';
        }
    }

    return html;
}


/* ============================================================
   APAGAR LOTE
   ============================================================ */
function apagarLote(lote_id) {
    if (!lote_id) { return; }

    if (!confirm('Apagar este lote e TODAS as cartelas dele?')) {
        return;
    }

    console.log('[apagarLote]', lote_id);

    fetch('/api/apagar_lote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lote_id: lote_id })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        console.log('[apagarLote] Resposta:', data);
        if (data.status === 'ok') {
            alert(data.cartelas_apagadas + ' cartelas apagadas!');
            location.reload();
        } else {
            alert('Erro: ' + (data.msg || 'desconhecido'));
        }
    })
    .catch(function (err) {
        console.error('[apagarLote] Erro:', err);
        alert('Erro: ' + String(err));
    });
}


/* ============================================================
   CONFERIR TODOS
   ============================================================ */
function conferirTodos() {
    if (!confirm('Conferir TODAS as cartelas pendentes?')) { return; }

    console.log('[conferirTodos] Iniciando...');

    fetch('/api/conferir', { method: 'POST' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        console.log('[conferirTodos] Resposta:', data);
        alert((data.conferidas || 0) + ' cartelas conferidas.');
        location.reload();
    })
    .catch(function (err) {
        console.error('[conferirTodos] Erro:', err);
        alert('Erro: ' + String(err));
    });
}