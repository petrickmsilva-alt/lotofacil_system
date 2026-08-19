/* AGENTE.JS - ES5 puro */

document.addEventListener('DOMContentLoaded', function () {

    /* Atualizar custo */
    document.getElementById('ag-qtd').oninput = function () {
        var qtd   = parseInt(this.value, 10) || 0;
        var custo = (qtd * 3.50).toFixed(2);
        document.getElementById('ag-custo').textContent = 'R$ ' + custo;
    };

    document.getElementById('btn-ag-gerar').onclick    = gerarComAgente;
    document.getElementById('btn-ag-calibrar').onclick = calibrarFiltros;
    document.getElementById('btn-ag-backtest').onclick = executarBacktest;
    document.getElementById('btn-att-log').onclick     = atualizarLog;
});


function gerarComAgente() {
    var qtd      = parseInt(document.getElementById('ag-qtd').value, 10);
    var modo     = document.getElementById('ag-modo').value;
    var concurso = parseInt(document.getElementById('ag-concurso').value, 10);
    var btn      = document.getElementById('btn-ag-gerar');
    var painel   = document.getElementById('resultado-agente');
    var conteudo = document.getElementById('conteudo-agente');

    btn.disabled   = true;
    btn.textContent = 'Gerando...';
    painel.className = 'section painel-visivel';
    conteudo.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> ' +
        'Agente processando ' + qtd + ' cartelas no modo ' +
        modo + '...</p>';

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/agente/gerar', true);
    xhr.setRequestHeader('Content-Type', 'application/json');

    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        btn.disabled    = false;
        btn.innerHTML   = '<i class="fas fa-robot"></i> Gerar com Agente';

        if (xhr.status === 200) {
            var data = null;
            try { data = JSON.parse(xhr.responseText); } catch (e) { return; }

            if (data.status === 'ok') {
                conteudo.innerHTML = montarResultadoAgente(data);
                atualizarLog();
            } else {
                conteudo.innerHTML =
                    '<p class="alert alert-danger">' + data.msg + '</p>';
            }
        } else {
            conteudo.innerHTML =
                '<p class="alert alert-danger">Erro HTTP: ' +
                xhr.status + '</p>';
        }
    };

    xhr.send(JSON.stringify({
        quantidade: qtd,
        modo:       modo,
        concurso:   concurso,
    }));
}


function montarResultadoAgente(data) {
    var html     = '';
    var cartelas = data.cartelas || [];
    var metr     = data.metricas || {};
    var elite    = data.grupo_elite || [];
    var i, j;

    /* Métricas */
    html += '<div class="agente-metricas">';
    html += '<div class="met-item">' +
            '<span>' + cartelas.length + '</span>' +
            '<label>Cartelas</label></div>';
    html += '<div class="met-item">' +
            '<span>R$ ' + (data.custo || 0).toFixed(2) + '</span>' +
            '<label>Custo Total</label></div>';
    html += '<div class="met-item">' +
            '<span>Concurso ' + (data.concurso_alvo || '?') + '</span>' +
            '<label>Alvo</label></div>';

    var cob13 = metr.cobertura_13 ? (metr.cobertura_13 * 100).toFixed(1) : '—';
    html += '<div class="met-item">' +
            '<span>' + cob13 + '%</span>' +
            '<label>Cobertura 13pts</label></div>';
    html += '</div>';

    /* Grupo Elite */
    if (elite.length > 0) {
        html += '<div style="margin-bottom:16px;">';
        html += '<strong>Grupo Elite selecionado pelo Agente:</strong>';
        html += '<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;">';
        for (i = 0; i < elite.length; i++) {
            var e   = parseInt(elite[i], 10);
            var pad = e < 10 ? '0' : '';
            html += '<span class="bola-mini" ' +
                    'style="background:rgba(108,92,231,0.3);">' +
                    pad + e + '</span>';
        }
        html += '</div></div>';
    }

    /* Cartelas */
    html += '<div class="cartelas-grid">';

    for (i = 0; i < cartelas.length; i++) {
        var c    = cartelas[i];
        var dez  = c.dezenas || [];
        var ev   = parseFloat(c.ev || 0).toFixed(6);
        var soma = c.soma || 0;
        var cob  = c.cobertura_13;
        var cobStr = cob !== undefined ?
                     (cob * 100).toFixed(1) + '%' : '—';

        html += '<div class="cartela-card">';
        html += '<div class="cartela-header">';
        html += '<span class="cartela-num">#' + (i + 1) + '</span>';
        html += '<span class="cartela-score">EV: ' + ev + '</span>';
        html += '</div>';

        /* Volante */
        html += '<div class="volante">';
        for (j = 1; j <= 25; j++) {
            var sel = dez.indexOf(j) >= 0 ? ' selecionada' : '';
            var pad2 = j < 10 ? '0' : '';
            html += '<div class="bola' + sel + '">' + pad2 + j + '</div>';
        }
        html += '</div>';

        /* Dezenas */
        html += '<div class="cartela-dezenas">';
        for (j = 0; j < dez.length; j++) {
            var dn   = parseInt(dez[j], 10);
            var pad3 = dn < 10 ? '0' : '';
            html += '<span class="dezena">' + pad3 + dn + '</span>';
        }
        html += '</div>';

        /* Info */
        html += '<div class="cartela-scores">';
        html += 'Soma:' + soma + ' | Pares:' + (c.pares||0) +
                ' | Primos:' + (c.primos||0) +
                ' | Cob13:' + cobStr;
        html += '</div>';
        html += '</div>';
    }

    html += '</div>';
    return html;
}


function calibrarFiltros() {
    var btn = document.getElementById('btn-ag-calibrar');
    btn.disabled    = true;
    btn.textContent = 'Calibrando...';

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/agente/calibrar', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        btn.disabled    = false;
        btn.textContent = 'Recalibrar Filtros';

        if (xhr.status === 200) {
            var data = JSON.parse(xhr.responseText);
            if (data.status === 'ok') {
                alert('Filtros calibrados com sucesso!\n' +
                      'Soma: ' + data.soma[0] + '-' + data.soma[1] + '\n' +
                      'Pares: ' + data.pares[0] + '-' + data.pares[1]);
                location.reload();
            } else {
                alert(data.status + ': ' + (data.msg || ''));
            }
        }
    };
    xhr.send();
}


function executarBacktest() {
    var btn = document.getElementById('btn-ag-backtest');
    btn.disabled    = true;
    btn.textContent = 'Executando...';

    var painel   = document.getElementById('resultado-agente');
    var conteudo = document.getElementById('conteudo-agente');
    painel.className   = 'section painel-visivel';
    conteudo.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> ' +
                         'Backtesting autônomo em andamento...</p>';

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/agente/backtesting', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        btn.disabled    = false;
        btn.textContent = 'Backtesting';

        if (xhr.status === 200) {
            var data = JSON.parse(xhr.responseText);
            conteudo.innerHTML = montarBacktest(data);
        }
    };
    xhr.send(JSON.stringify({ n_testes: 20, n_cartelas: 5 }));
}


function montarBacktest(data) {
    if (data.status !== 'ok') {
        return '<p class="alert alert-danger">' +
               (data.status) + '</p>';
    }
    var html = '<h3>Resultado do Backtesting</h3>';
    html += '<div class="agente-metricas">';
    html += '<div class="met-item"><span>' + data.total_testes +
            '</span><label>Testes</label></div>';
    html += '<div class="met-item"><span>' + data.total_cartelas +
            '</span><label>Cartelas</label></div>';
    html += '<div class="met-item"><span>' +
            (data.taxa_13 * 100).toFixed(2) + '%</span>' +
            '<label>Taxa 13pts</label></div>';
    html += '<div class="met-item"><span>' +
            (data.taxa_14 * 100).toFixed(2) + '%</span>' +
            '<label>Taxa 14pts</label></div>';
    html += '<div class="met-item"><span>' +
            (data.taxa_15 * 100).toFixed(2) + '%</span>' +
            '<label>Taxa 15pts</label></div>';
    html += '</div>';

    var dist = data.distribuicao || {};
    html += '<h3 style="margin-top:16px;">Distribuição de Acertos:</h3>';
    html += '<table class="table" style="margin-top:8px;">';
    html += '<thead><tr><th>Acertos</th><th>Qtd</th></tr></thead><tbody>';
    var faixas = [11, 12, 13, 14, 15];
    for (var i = 0; i < faixas.length; i++) {
        var f = faixas[i];
        html += '<tr><td>' + f + ' pontos</td>' +
                '<td>' + (dist[f] || 0) + '</td></tr>';
    }
    html += '</tbody></table>';
    return html;
}


function atualizarLog() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/agente/log', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4 || xhr.status !== 200) { return; }
        var data = JSON.parse(xhr.responseText);
        var log  = data.log || [];
        var div  = document.getElementById('log-agente');
        var html = '';
        var i    = log.length - 1;
        while (i >= 0) {
            var e = log[i];
            html += '<div class="log-linha">' +
                    '<span class="log-ts">' + (e.ts || '') + '</span>' +
                    '<span class="log-tipo tipo-' + (e.tipo || '') + '">' +
                    '[' + (e.tipo || '') + ']</span>' +
                    '<span class="log-msg">' + (e.msg || '') + '</span>' +
                    '</div>';
            i = i - 1;
        }
        div.innerHTML = html || '<p style="color:#888;">Sem log.</p>';
    };
    xhr.send();
}