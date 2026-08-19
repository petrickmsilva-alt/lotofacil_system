/* ============================================================
   CICLO.JS - ES5 puro
   ============================================================ */

var pollingLog = null;

document.addEventListener('DOMContentLoaded', function () {

    /* Barras de peso */
    aplicarBarras();

    /* Botões de controle */
    document.getElementById('btn-iniciar').onclick = iniciarLoop;
    document.getElementById('btn-pausar').onclick  = pausarLoop;
    document.getElementById('btn-retomar').onclick = retomarLoop;
    document.getElementById('btn-parar').onclick   = pararLoop;
    document.getElementById('btn-manual').onclick  = executarManual;

    /* Atualizar histórico */
    document.getElementById('btn-att-hist').onclick = atualizarHistorico;

    /* Limpar log */
    document.getElementById('btn-limpar-log').onclick = function () {
        document.getElementById('log-ciclo').innerHTML = '';
    };

    /* Fechar modal */
    document.getElementById('btn-fechar-ciclo').onclick = fecharModal;
    document.getElementById('modal-ciclo-bg').onclick   = fecharModal;

    /* Botões ver ciclo */
    vincularVerCiclo();

    /* Polling do log a cada 5s */
    pollingLog = setInterval(atualizarLog, 5000);

    document.onkeydown = function (e) {
        if (e.key === 'Escape' || e.keyCode === 27) { fecharModal(); }
    };
});

function aplicarBarras() {
    var barras = document.querySelectorAll('.mini-fill, .peso-fill');
    var i = 0;
    while (i < barras.length) {
        var w = parseInt(barras[i].getAttribute('data-width') || '0', 10);
        barras[i].style.width = w + '%';
        i = i + 1;
    }
}

function fecharModal() {
    document.getElementById('modal-ciclo').style.display = 'none';
}

/* ── Controles do loop ─────────────────────────────────────── */
function iniciarLoop() {
    var nc  = parseInt(document.getElementById('n-cartelas').value,  10) || 10;
    var inv = parseInt(document.getElementById('intervalo').value,    10) || 3600;

    /* Configurar n_cartelas */
    var xhrC = new XMLHttpRequest();
    xhrC.open('POST', '/api/ciclo/configurar', true);
    xhrC.setRequestHeader('Content-Type', 'application/json');
    xhrC.send(JSON.stringify({ n_cartelas: nc }));

    /* Iniciar loop */
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/ciclo/iniciar', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        var data = JSON.parse(xhr.responseText);
        mostrarNotificacao(
            data.status === 'iniciado' ?
                'Loop iniciado! Intervalo: ' + inv + 's' :
                data.status,
            data.status === 'iniciado' ? 'success' : 'danger'
        );
        atualizarStatus();
    };
    xhr.send(JSON.stringify({ intervalo: inv }));
}

function pausarLoop() {
    chamarAPI('/api/ciclo/pausar', 'Ciclo pausado.', 'warning');
}

function retomarLoop() {
    chamarAPI('/api/ciclo/retomar', 'Ciclo retomado.', 'success');
}

function pararLoop() {
    if (!confirm('Parar o loop automático?')) { return; }
    chamarAPI('/api/ciclo/parar', 'Loop parado.', 'danger');
}

function chamarAPI(url, msg, tipo) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        mostrarNotificacao(msg, tipo);
        atualizarStatus();
    };
    xhr.send();
}

/* ── Ciclo manual ──────────────────────────────────────────── */
function executarManual() {
    var inp = document.getElementById('concurso-manual');
    var num = parseInt(inp.value, 10);
    if (!num || num < 1) {
        alert('Informe o número do concurso.');
        return;
    }

    var btn = document.getElementById('btn-manual');
    btn.disabled    = true;
    btn.textContent = 'Executando...';

    mostrarNotificacao(
        'Ciclo ' + num + ' iniciado em background...', 'success'
    );

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/ciclo/executar_manual', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        btn.disabled    = false;
        btn.innerHTML   = '<i class="fas fa-bolt"></i> Executar Ciclo';
        atualizarHistorico();
        atualizarLog();
    };
    xhr.send(JSON.stringify({ concurso: num }));
}

/* ── Status em tempo real ──────────────────────────────────── */
function atualizarStatus() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/ciclo/status', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4 || xhr.status !== 200) { return; }
        var data = JSON.parse(xhr.responseText);

        var txtEstado = document.getElementById('txt-estado');
        if (txtEstado) { txtEstado.textContent = data.estado; }

        var icoEstado = document.getElementById('ico-estado');
        if (icoEstado) {
            icoEstado.style.color =
                data.estado === 'monitorando' ? 'var(--success)' :
                data.estado === 'pausado'     ? 'var(--warning)' :
                data.estado === 'gerando'     ? 'var(--primary)' :
                                                'var(--danger)';
        }
    };
    xhr.send();
}

/* ── Log em tempo real ─────────────────────────────────────── */
function atualizarLog() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/ciclo/status', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4 || xhr.status !== 200) { return; }
        var data = JSON.parse(xhr.responseText);
        var log  = data.log_recente || [];
        var div  = document.getElementById('log-ciclo');
        if (!div) { return; }

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
        if (html) { div.innerHTML = html; }
    };
    xhr.send();
}

/* ── Histórico ─────────────────────────────────────────────── */
function atualizarHistorico() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/ciclo/historico', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4 || xhr.status !== 200) { return; }
        var data = JSON.parse(xhr.responseText);
        var hist = data.historico || [];
        var tbody = document.getElementById('tbody-historico');
        if (!tbody) { return; }

        var html = '';
        var i    = 0;
        while (i < hist.length) {
            var h   = hist[i];
            var cls = h.status === 'completo'     ? 'badge-success' :
                      h.status === 'em_andamento'  ? 'badge-warning' :
                                                     'badge-danger';
            var clsA = h.melhor_acertos >= 13 ? 'badge-success' :
                       h.melhor_acertos >= 11 ? 'badge-warning' :
                                                'badge-sem_premio';
            html += '<tr>' +
                    '<td><strong>' + h.concurso + '</strong></td>' +
                    '<td style="font-size:12px;">' +
                    (h.timestamp_inicio || '') + '</td>' +
                    '<td><span class="badge ' + cls + '">' +
                    h.status + '</span></td>' +
                    '<td>' + (h.n_cartelas || 0) + '</td>' +
                    '<td><span class="badge ' + clsA + '">' +
                    (h.melhor_acertos || 0) + ' pts</span></td>' +
                    '<td>' + (h.total_ganho > 0 ?
                        '<span class="valor positivo">R$ ' +
                        parseFloat(h.total_ganho).toFixed(2) + '</span>' :
                        '—') + '</td>' +
                    '<td>' +
                    '<button class="btn btn-sm btn-outline btn-ver-ciclo" ' +
                    'data-concurso="' + h.concurso + '">' +
                    'Ver</button></td>' +
                    '</tr>';
            i = i + 1;
        }
        tbody.innerHTML = html || '<tr><td colspan="7" ' +
            'style="text-align:center;color:var(--text-muted);">' +
            'Sem histórico.</td></tr>';
        vincularVerCiclo();
    };
    xhr.send();
}

/* ── Ver detalhes do ciclo ─────────────────────────────────── */
function vincularVerCiclo() {
    var btns = document.querySelectorAll('.btn-ver-ciclo');
    var i    = 0;
    while (i < btns.length) {
        btns[i].onclick = function () {
            var conc = parseInt(this.getAttribute('data-concurso'), 10);
            verDetalhes(conc);
        };
        i = i + 1;
    }
}

function verDetalhes(concurso) {
    var modal  = document.getElementById('modal-ciclo');
    var titulo = document.getElementById('modal-ciclo-titulo');
    var corpo  = document.getElementById('modal-ciclo-corpo');

    modal.style.display = 'flex';
    titulo.textContent  = 'Ciclo — Concurso ' + concurso;
    corpo.innerHTML     = '<p>Carregando...</p>';

    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/ciclo/fila/' + concurso, true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4 || xhr.status !== 200) { return; }
        var data = JSON.parse(xhr.responseText);
        corpo.innerHTML = montarDetalhesCiclo(data.fila || [], concurso);
    };
    xhr.send();
}

function montarDetalhesCiclo(fila, concurso) {
    var html = '';
    var i, j;

    if (fila.length === 0) {
        return '<p style="color:var(--text-muted);">' +
               'Sem cartelas na fila para o concurso ' + concurso + '</p>';
    }

    html += '<p style="color:var(--text-muted);margin-bottom:16px;">' +
            fila.length + ' cartelas | Concurso ' + concurso + '</p>';

    /* Resumo */
    var premiadas = 0;
    var total_g   = 0;
    for (i = 0; i < fila.length; i++) {
        if (parseInt(fila[i].acertos || 0, 10) >= 11) { premiadas += 1; }
        total_g += parseFloat(fila[i].premio_ganho || 0);
    }

    html += '<div class="conf-resumo">';
    html += '<span><strong>' + fila.length + '</strong> cartelas</span>';
    html += '<span><strong style="color:var(--success);">' +
            premiadas + '</strong> premiadas</span>';
    if (total_g > 0) {
        html += '<span><strong style="color:var(--success);">' +
                'R$ ' + total_g.toFixed(2) + '</strong> ganho</span>';
    }
    html += '</div>';

    /* Cartelas */
    for (i = 0; i < fila.length; i++) {
        var c   = fila[i];
        var dez = c.dezenas || [];
        var ac  = parseInt(c.acertos || 0, 10);
        var prem = parseFloat(c.premio_ganho || 0);

        var acert   = c.dezenas_acertadas || [];
        var setA    = {};
        for (j = 0; j < acert.length; j++) { setA[acert[j]] = true; }

        var fundo = 'var(--dark-3)';
        if      (ac >= 15) { fundo = 'rgba(225,112,85,0.2)'; }
        else if (ac >= 14) { fundo = 'rgba(108,92,231,0.2)'; }
        else if (ac >= 13) { fundo = 'rgba(0,184,148,0.2)';  }
        else if (ac >= 12) { fundo = 'rgba(253,203,110,0.15)'; }
        else if (ac >= 11) { fundo = 'rgba(116,185,255,0.15)'; }

        html += '<div class="cartela-conf" style="background:' + fundo + ';">';
        html += '<div class="cartela-conf-header">';
        html += '<strong>#' + c.id + '</strong>';

        var status = c.status || 'aguardando';
        html += '<span class="badge badge-' + status + '">';
        if (ac > 0) {
            html += ac + ' pts';
        } else {
            html += status;
        }
        html += '</span>';

        if (prem > 0) {
            html += '<span style="color:var(--success);font-weight:700;">' +
                    'R$ ' + prem.toFixed(2) + '</span>';
        }

        var erroP = parseFloat(c.erro_previsao || 0);
        html += '<span style="font-size:11px;color:var(--text-muted);">' +
                'Erro prev.: ' + erroP.toFixed(4) + '</span>';
        html += '</div>';

        /* Bolas */
        html += '<div style="display:flex;flex-wrap:wrap;gap:4px;margin:8px 0;">';
        for (j = 0; j < dez.length; j++) {
            var dn   = parseInt(dez[j], 10);
            var pad  = dn < 10 ? '0' : '';
            var cls  = setA[dn] ? 'bola-mini selecionada' : 'bola-mini';
            html += '<span class="' + cls + '">' + pad + dn + '</span>';
        }
        html += '</div>';

        /* Score */
        html += '<div style="font-size:11px;color:var(--text-muted);">' +
                'Score: ' + parseFloat(c.score_total || 0).toFixed(4) +
                '</div>';
        html += '</div>';
    }

    return html;
}

/* ── Notificação ───────────────────────────────────────────── */
function mostrarNotificacao(msg, tipo) {
    var div = document.createElement('div');
    div.className   = 'notificacao notif-' + (tipo || 'success');
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(function () {
        if (div.parentNode) { div.parentNode.removeChild(div); }
    }, 4000);
}

/* Atualizar status a cada 10s */
setInterval(atualizarStatus, 10000);