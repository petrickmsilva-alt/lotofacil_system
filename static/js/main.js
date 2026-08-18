/* ============================================================
   LOTOFÁCIL IA - JAVASCRIPT PRINCIPAL
   ============================================================ */

// ── Controle inicial do painel de progresso ──────────────────
document.addEventListener('DOMContentLoaded', function () {

    // Mostrar progresso se sistema estiver carregando/treinando
    verificarEstadoInicial();

    // Highlight do menu ativo
    var path = window.location.pathname;
    document.querySelectorAll('.nav-menu a').forEach(function (link) {
        if (link.getAttribute('href') === path) {
            link.classList.add('active');
        }
    });

    console.log([
        '╔══════════════════════════════════════╗',
        '║  LotoFácil IA - Sistema Ativo        ║',
        '║  Quantum Engine v1.0                 ║',
        '╚══════════════════════════════════════╝'
    ].join('\n'));
});

// ── Verifica estado inicial via API ─────────────────────────
function verificarEstadoInicial() {
    fetch('/api/status')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.carregando || data.treinando) {
                mostrarProgresso(data.progresso || 'Processando...');
                iniciarPolling();
            }
        })
        .catch(function () {});
}

// ── Mostra/esconde painel de progresso ──────────────────────
function mostrarProgresso(texto) {
    var section = document.getElementById('progress-section');
    var textEl  = document.getElementById('progress-text');
    var fill    = document.getElementById('progress-fill');

    if (section) {
        section.classList.remove('progress-hidden');
        section.classList.add('progress-visible');
    }
    if (textEl && texto) {
        textEl.textContent = texto;
    }
    if (fill) {
        fill.style.width = '70%';
    }
}

function esconderProgresso() {
    var section = document.getElementById('progress-section');
    if (section) {
        section.classList.remove('progress-visible');
        section.classList.add('progress-hidden');
    }
}

// ── Atualizar status ─────────────────────────────────────────
function atualizarStatus() {
    fetch('/api/status')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            // Atualizar texto de progresso no topbar
            var progresso = document.getElementById('progresso-status');
            if (progresso) {
                progresso.textContent = data.progresso || '';
            }

            // Atualizar texto interno
            var progressText = document.getElementById('progress-text');
            if (progressText) {
                progressText.textContent = data.progresso || '';
            }

            // Mostrar ou esconder painel
            if (data.carregando || data.treinando) {
                mostrarProgresso(data.progresso);
            } else {
                esconderProgresso();
            }
        })
        .catch(function (err) {
            console.log('Erro ao buscar status:', err);
        });
}

// ── Polling automático ───────────────────────────────────────
var pollingInterval = null;

function iniciarPolling() {
    if (pollingInterval) { return; } // já está rodando
    pollingInterval = setInterval(function () {
        fetch('/api/status')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var progresso = document.getElementById('progresso-status');
                if (progresso) { progresso.textContent = data.progresso || ''; }

                var progressText = document.getElementById('progress-text');
                if (progressText) { progressText.textContent = data.progresso || ''; }

                if (data.carregando || data.treinando) {
                    mostrarProgresso(data.progresso);
                } else {
                    // Concluído
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    esconderProgresso();

                    if (data.progresso && data.progresso.indexOf('✅') !== -1) {
                        setTimeout(function () { location.reload(); }, 1500);
                    }
                }
            });
    }, 2500);
}

// ── Carregar dados da Caixa ──────────────────────────────────
function carregarDados() {
    if (!confirm(
        'Carregar TODO o histórico da Lotofácil?\n' +
        'Isso pode demorar alguns minutos na primeira vez.'
    )) { return; }

    fetch('/api/carregar_dados', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            mostrarProgresso(data.msg || 'Carregando...');
            iniciarPolling();
        })
        .catch(function (err) {
            alert('Erro ao iniciar carregamento: ' + err);
        });
}

// ── Atualizar apenas dados novos ─────────────────────────────
function atualizarDados() {
    mostrarProgresso('Verificando novos concursos...');

    fetch('/api/atualizar_dados', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            esconderProgresso();
            if (data.status === 'ok') {
                alert(data.msg || (data.novos_concursos + ' novos concursos carregados'));
                location.reload();
            } else {
                alert('Erro: ' + data.msg);
            }
        })
        .catch(function (err) {
            esconderProgresso();
            alert('Erro: ' + err);
        });
}

// Atualização diária automática
function atualizarDiario() {
    mostrarProgresso('Buscando novos concursos da Caixa...');
    fetch('/api/atualizar_diario', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            esconderProgresso();
            var msg = data.msg || 'Atualizado!';
            alert(msg);
            if (data.novos > 0) { location.reload(); }
        })
        .catch(function (err) {
            esconderProgresso();
            alert('Erro na atualização: ' + err);
        });
}

// ── Treinar IA ───────────────────────────────────────────────
function treinarIA() {
    if (!confirm(
        'Iniciar treinamento da IA?\n' +
        'Isso pode levar alguns minutos dependendo do histórico.'
    )) { return; }

    fetch('/api/treinar_ia', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            mostrarProgresso(data.msg || 'Treinando...');
            iniciarPolling();
        })
        .catch(function (err) {
            alert('Erro ao iniciar treinamento: ' + err);
        });
}

// ── Conferir jogos ───────────────────────────────────────────
function conferirTodos() {
    mostrarProgresso('Conferindo cartelas...');

    fetch('/api/conferir', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            esconderProgresso();
            if (data.status === 'ok') {
                alert(data.conferidas + ' cartelas conferidas!');
                location.reload();
            } else {
                alert('Erro: ' + data.msg);
            }
        })
        .catch(function (err) {
            esconderProgresso();
            alert('Erro: ' + err);
        });
}

// ── Auto-update a cada 30s ───────────────────────────────────
setInterval(atualizarStatus, 30000);