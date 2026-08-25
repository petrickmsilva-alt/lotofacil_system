/* ============================================================
   MAIN.JS — Gerenciador Global de Interface
   ============================================================ */

var emProcessamento = false;

document.addEventListener('DOMContentLoaded', function () {
    // 1. Esconde a barra de progresso imediatamente ao carregar a página
    var progressSection = document.getElementById('progress-section');
    if (progressSection) {
        progressSection.style.display = 'none';
    }

    // 2. Marca o menu ativo
    var path = window.location.pathname;
    var links = document.querySelectorAll('.nav-menu a');
    for (var i = 0; i < links.length; i++) {
        if (links[i].getAttribute('href') === path) {
            links[i].classList.add('active');
        }
    }

    // 3. Puxa os status do servidor
    atualizarStatus();
});


/* ── Atualizar Status Global ───────────────────────────────── */
function atualizarStatus() {
    fetch('/api/status')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            
            // Texto superior (topbar)
            var progressoTexto = document.getElementById('progresso-status');
            if (progressoTexto) { 
                progressoTexto.textContent = data.progresso || ''; 
            }

            // Texto dentro da caixa de progresso
            var progressText = document.getElementById('progress-text');
            if (progressText) { 
                progressText.textContent = data.progresso || ''; 
            }

            // Controle da caixa de progresso
            var progressSection = document.getElementById('progress-section');
            var rodando = data.carregando || data.treinando;

            if (progressSection) {
                if (rodando) {
                    progressSection.style.display = 'block';
                    emProcessamento = true;
                } else {
                    progressSection.style.display = 'none';
                    
                    // Se a IA acabou de treinar, recarrega a página para atualizar os cards
                    if (emProcessamento) {
                        emProcessamento = false;
                        location.reload();
                    }
                }
            }

            // Atualiza Rodapé (IA Online/Offline e Concursos)
            var statusDivs = document.querySelectorAll('.sidebar-footer .status-indicator');
            if (statusDivs && statusDivs.length >= 2) {
                var isOnline = data.ia_treinada;
                statusDivs[0].innerHTML = '<span class="dot ' + (isOnline ? 'green' : 'red') + '"></span> IA: ' + (isOnline ? 'Online' : 'Offline');
                
                var qtdDados = data.ultimo_concurso || 0;
                statusDivs[1].innerHTML = '<span class="dot ' + (qtdDados > 0 ? 'green' : 'red') + '"></span> Dados: ' + qtdDados + ' concursos';
            }
        })
        .catch(function (err) { console.log('Erro Status:', err); });
}


/* ── Ações de Botões (Dashboard) ───────────────────────────── */
function carregarDados() {
    if (!confirm('Carregar histórico da Caixa? Isso pode demorar.')) { return; }
    
    var progressSection = document.getElementById('progress-section');
    if (progressSection) progressSection.style.display = 'block';
    emProcessamento = true;

    fetch('/api/carregar_dados', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function () { atualizarStatus(); });
}

function treinarIA() {
    if (!confirm('Assimilar novamente todo o histórico na memória única da Inteligência Magna?')) { return; }
    
    var progressSection = document.getElementById('progress-section');
    if (progressSection) progressSection.style.display = 'block';
    emProcessamento = true;

    fetch('/api/treinar_ia', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function () { atualizarStatus(); });
}



/* ── Sincronizar histórico incremental ─────────────────────── */
function atualizarDados() {
    var botao = document.getElementById('btn-atualizar-historico');
    var mensagem = document.getElementById('historico-update-status');
    if (botao) { botao.disabled = true; }
    if (mensagem) { mensagem.textContent = 'Consultando fontes de resultados…'; }

    fetch('/api/atualizar_dados', { method: 'POST' })
        .then(function (r) {
            return r.json().then(function (data) {
                if (!r.ok && r.status !== 409) {
                    throw new Error(data.msg || 'Falha ao iniciar atualização');
                }
                return data;
            });
        })
        .then(function () { aguardarAtualizacaoHistorico(botao, mensagem); })
        .catch(function (err) {
            if (botao) { botao.disabled = false; }
            if (mensagem) { mensagem.textContent = 'Erro: ' + err.message; }
        });
}

function aguardarAtualizacaoHistorico(botao, mensagem) {
    fetch('/api/status')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (mensagem) { mensagem.textContent = data.progresso || ''; }
            if (data.carregando) {
                setTimeout(function () {
                    aguardarAtualizacaoHistorico(botao, mensagem);
                }, 1200);
                return;
            }
            if (data.erro_atualizacao) {
                if (botao) { botao.disabled = false; }
                if (mensagem) {
                    mensagem.textContent = 'Atualização parcial/erro: ' +
                        data.erro_atualizacao;
                }
                return;
            }
            window.location.reload();
        })
        .catch(function (err) {
            if (botao) { botao.disabled = false; }
            if (mensagem) { mensagem.textContent = 'Erro: ' + err.message; }
        });
}

// Atualiza sozinho a cada 5 segundos
setInterval(atualizarStatus, 5000);