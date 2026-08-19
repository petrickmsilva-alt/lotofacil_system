/* ============================================================
   CEREBRO.JS — Painel do Cérebro IA
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

    aplicarBarras();

    var btnTreinar = document.getElementById('btn-treinar');
    var btnIniciar = document.getElementById('btn-iniciar-loop');
    var btnPausar  = document.getElementById('btn-pausar');
    var btnParar   = document.getElementById('btn-parar');
    var btnLimpar  = document.getElementById('btn-limpar-log');

    if (btnTreinar) { btnTreinar.onclick = treinarCerebro; }
    if (btnIniciar) { btnIniciar.onclick = iniciarLoop;    }
    if (btnPausar)  { btnPausar.onclick  = pausarLoop;     }
    if (btnParar)   { btnParar.onclick   = pararLoop;      }
    if (btnLimpar) {
        btnLimpar.onclick = function () {
            document.getElementById('log-cerebro').innerHTML = '';
        };
    }

    /* Polling a cada 8s */
    setInterval(atualizarStatus, 8000);
    setInterval(atualizarLog,    8000);
});


function aplicarBarras() {
    var els = document.querySelectorAll('.peso-fill');
    var i   = 0;
    while (i < els.length) {
        var w = parseInt(els[i].getAttribute('data-width') || '0', 10);
        els[i].style.width = w + '%';
        i = i + 1;
    }
}


function atualizarStatus() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/cerebro/status', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4 || xhr.status !== 200) { return; }
        try {
            var data = JSON.parse(xhr.responseText);
            var txt  = document.getElementById('txt-estado');
            var ico  = document.getElementById('ico-estado');
            if (txt) { txt.textContent = data.estado || '—'; }
            if (ico) {
                var cor = 'var(--danger)';
                if (data.estado === 'monitorando') { cor = 'var(--success)'; }
                else if (data.estado === 'gerando')    { cor = 'var(--primary)'; }
                else if (data.estado === 'pausado')    { cor = 'var(--warning)'; }
                else if (data.estado === 'pronto')     { cor = 'var(--success)'; }
                ico.style.color = cor;
            }
        } catch (e) {}
    };
    xhr.send();
}


function atualizarLog() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/cerebro/log', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4 || xhr.status !== 200) { return; }
        try {
            var data = JSON.parse(xhr.responseText);
            var log  = data.log || [];
            var div  = document.getElementById('log-cerebro');
            if (!div || log.length === 0) { return; }

            var html = '';
            var i    = log.length - 1;
            while (i >= 0) {
                var e = log[i];
                html += '<div class="log-linha">' +
                    '<span class="log-ts">'   + (e.ts   || '') + '</span>' +
                    '<span class="log-tipo tipo-' + (e.tipo || '') + '">' +
                    '[' + (e.tipo || '') + ']</span>' +
                    '<span class="log-msg">'  + (e.msg  || '') + '</span>' +
                    '</div>';
                i = i - 1;
            }
            div.innerHTML = html;
        } catch (e) {}
    };
    xhr.send();
}


function treinarCerebro() {
    if (!confirm('Treinar os 14 módulos do Cérebro? Pode levar alguns minutos.')) {
        return;
    }

    var btn = document.getElementById('btn-treinar');
    btn.disabled  = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Treinando...';

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/treinar_ia', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        btn.disabled  = false;
        btn.innerHTML = '<i class="fas fa-graduation-cap"></i> Treinar 14 Módulos';

        alert('Treinamento iniciado em background!\n' +
              'Acompanhe pelo log.');
    };
    xhr.send();
}


function iniciarLoop() {
    if (!confirm('Iniciar loop autônomo? O Cérebro vai monitorar a Caixa e gerar cartelas sozinho.')) {
        return;
    }

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/cerebro/loop/iniciar', true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) { return; }
        try {
            var data = JSON.parse(xhr.responseText);
            alert(data.status === 'iniciado' ?
                  'Loop autônomo iniciado!' :
                  'Loop: ' + data.status);
        } catch (e) { alert('Erro ao iniciar loop.'); }
    };
    xhr.send(JSON.stringify({ intervalo: 3600, n_cartelas: 10 }));
}


function pausarLoop() {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/cerebro/loop/pausar', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) { alert('Cérebro pausado.'); }
    };
    xhr.send();
}


function pararLoop() {
    if (!confirm('Parar o loop autônomo?')) { return; }
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/cerebro/loop/parar', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) { alert('Loop parado.'); }
    };
    xhr.send();
}