/* ============================================================
   AUDITORIA DA IA - JavaScript puro ES5
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

    /* Aplicar larguras das mini-barras */
    var barras = document.querySelectorAll('.mini-fill');
    var i = 0;
    while (i < barras.length) {
        var w = parseInt(barras[i].getAttribute('data-width') || '0', 10);
        if (w > 100) { w = 100; }
        if (w < 0)   { w = 0;   }
        barras[i].style.width = w + '%';
        i = i + 1;
    }

    /* Botoes Ver Sessao */
    var botoes = document.querySelectorAll('.btn-ver-sessao');
    var j = 0;
    while (j < botoes.length) {
        var btn = botoes[j];
        var sid = btn.getAttribute('data-sessao-id');
        btn.onclick = function () {
            var id = this.getAttribute('data-sessao-id');
            abrirSessao(id);
        };
        j = j + 1;
    }

    /* Fechar modal pelo X */
    document.getElementById('btn-fechar-modal').onclick = fecharModal;

    /* Fechar modal clicando no fundo */
    document.getElementById('modal-fechar').onclick = fecharModal;

    /* Fechar modal com ESC */
    document.onkeydown = function (e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            fecharModal();
        }
    };

});


/* Abrir modal e carregar sessao */
function abrirSessao(id) {
    var modal   = document.getElementById('modal-sessao');
    var titulo  = document.getElementById('modal-titulo');
    var conteudo = document.getElementById('modal-conteudo');

    modal.style.display   = 'flex';
    titulo.textContent     = 'Sessao #' + id;
    conteudo.innerHTML     = '<p>Carregando dados da sessao...</p>';

    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/ia_sessao/' + id, true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                try {
                    var data = JSON.parse(xhr.responseText);
                    conteudo.innerHTML = construirHtml(data);
                } catch (err) {
                    conteudo.innerHTML =
                        '<p>Erro ao processar resposta.</p>';
                }
            } else {
                conteudo.innerHTML =
                    '<p>Erro HTTP: ' + xhr.status + '</p>';
            }
        }
    };
    xhr.send();
}


/* Fechar modal */
function fecharModal() {
    document.getElementById('modal-sessao').style.display = 'none';
}


/* Construir HTML dos detalhes da sessao */
function construirHtml(data) {
    var html     = '';
    var modulos  = data.modulos  || [];
    var decisoes = data.decisoes || [];
    var i, j;

    /* --- Secao Modulos --- */
    html += '<h3 style="margin-bottom:12px;">Modulos Executados</h3>';

    if (modulos.length === 0) {
        html += '<p style="color:#888;">Sem modulos registrados.</p>';
    } else {
        html += '<table class="table" style="font-size:12px;">';
        html += '<thead><tr>';
        html += '<th>Modulo</th>';
        html += '<th>Acao</th>';
        html += '<th>Score</th>';
        html += '<th>Top 3 Dezenas</th>';
        html += '<th>Tempo</th>';
        html += '<th>OK</th>';
        html += '</tr></thead><tbody>';

        for (i = 0; i < modulos.length; i++) {
            var m    = modulos[i];
            var icon = (m.status === 'ok') ? 'SIM' : 'NAO';
            var top3 = [];

            try {
                top3 = JSON.parse(m.top3_dezenas || '[]');
            } catch (e) {
                top3 = [];
            }

            var top3html = '';
            for (j = 0; j < top3.length; j++) {
                var num = parseInt(top3[j], 10);
                var pad = '';
                if (num < 10) { pad = '0'; }
                top3html += '<span class="bola-mini">' +
                            pad + num + '</span>';
            }

            var scoreStr = parseFloat(m.score_medio || 0).toFixed(4);
            var duracStr = parseFloat(m.duracao_ms  || 0).toFixed(0);

            html += '<tr>';
            html += '<td><strong>' + (m.modulo || '') + '</strong></td>';
            html += '<td>' + (m.acao   || '') + '</td>';
            html += '<td>' + scoreStr  + '</td>';
            html += '<td>' + top3html  + '</td>';
            html += '<td>' + duracStr  + 'ms</td>';
            html += '<td>' + icon      + '</td>';
            html += '</tr>';
        }
        html += '</tbody></table>';
    }

    /* --- Secao Cartelas --- */
    if (decisoes.length > 0) {
        html += '<h3 style="margin:20px 0 12px;">';
        html += 'Cartelas Geradas (' + decisoes.length + ')</h3>';

        /* Tabelas de mapeamento modulo -> chave */
        var nomes = [
            'markov', 'fisico', 'gaussiano',
            'ml', 'verlet', 'quantum',
            'chi2', 'bayes', 'kl'
        ];
        var chaves = [
            'score_markov', 'score_fisico', 'score_gaussiano',
            'score_ml', 'score_verlet', 'score_quantum',
            'score_chi2', 'score_bayes', 'score_kl'
        ];

        for (i = 0; i < decisoes.length; i++) {
            var d   = decisoes[i];
            var dez = [];

            try {
                dez = JSON.parse(d.dezenas || '[]');
            } catch (e) {
                dez = [];
            }

            var dezHtml = '';
            for (j = 0; j < dez.length; j++) {
                var dn  = parseInt(dez[j], 10);
                var pad = '';
                if (dn < 10) { pad = '0'; }
                dezHtml += '<span class="bola-mini selecionada">' +
                            pad + dn + '</span>';
            }

            var scoreTotal = parseFloat(d.score_total || 0).toFixed(4);
            var modLider   = d.modulo_dominante || 'N/A';

            html += '<div class="cartela-mini">';

            /* Cabecalho */
            html += '<div style="display:flex;justify-content:space-between;margin-bottom:8px;">';
            html += '<strong>Cartela #' + (i + 1) + '</strong>';
            html += '<span style="color:#00B894;">Score: ' + scoreTotal + '</span>';
            html += '</div>';

            /* Bolas */
            html += '<div style="margin-bottom:8px;">' + dezHtml + '</div>';

            /* Modulo lider */
            html += '<div style="font-size:11px;color:#888;margin-bottom:8px;">';
            html += 'Modulo lider: <strong>' + modLider + '</strong>';
            html += '</div>';

            /* Barras */
            html += '<div style="font-size:11px;">';

            for (j = 0; j < nomes.length; j++) {
                var nomeM  = nomes[j];
                var chaveM = chaves[j];
                var valM   = parseFloat(d[chaveM] || 0);
                var wPct   = Math.round(valM * 100);
                var valStr = valM.toFixed(3);

                html += '<div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">';
                html += '<span style="width:70px;color:#888;">' + nomeM + '</span>';
                html += '<div style="flex:1;height:8px;background:#2d2d5e;border-radius:4px;overflow:hidden;">';
                html += '<div style="width:' + wPct + '%;height:100%;background:#6C5CE7;border-radius:4px;"></div>';
                html += '</div>';
                html += '<span style="width:45px;text-align:right;">' + valStr + '</span>';
                html += '</div>';
            }

            html += '</div>';
            html += '</div>';
        }
    }

    return html;
}