/* ============================================================
   PAINEL DE PADRÕES DE ABERTURA — v11.3
   Menor dezena (lista ordenada) + ordem real da 1ª bola.
   Fonte única: GET /api/magna/ordem
   ============================================================ */
(function () {
  "use strict";

  var fmtPct = function (x, dec) {
    if (x === null || x === undefined || isNaN(x)) return "—";
    return (x * 100).toFixed(dec === undefined ? 1 : dec).replace(".", ",") + "%";
  };
  var el = function (id) { return document.getElementById(id); };

  function bar(pct, cls) {
    return '<div class="ordem-bar"><div class="ordem-bar-fill ' + (cls || "") +
      '" style="width:' + Math.max(2, Math.min(100, pct * 100)) + '%"></div></div>';
  }

  function vereditoBadge(v) {
    var real = v === "REAL";
    return '<span class="ordem-veredito ' + (real ? "real" : "ruido") + '">' +
      (real ? '<i class="fas fa-circle-check"></i> REAL' :
              '<i class="fas fa-flask"></i> RUÍDO (ruído estatístico)') + "</span>";
  }

  /* ---------------- Run atual (badge do hero) ---------------- */
  function renderRunAtual(md) {
    var run = md && md.streaks && md.streaks.run_atual;
    var box = el("ordem-run-atual");
    if (!run) {
      box.className = "ordem-badge atual";
      box.innerHTML = '<i class="fas fa-database"></i> sem dados';
      return;
    }
    box.className = "ordem-badge atual" + (run.comprimento >= 2 ? " quente" : "");
    box.innerHTML = "<strong>Abertura atual: " +
      String(run.dezena).padStart(2, "0") + "</strong> · " +
      run.comprimento + " concurso" + (run.comprimento > 1 ? "s" : "") +
      " seguido" + (run.comprimento > 1 ? "s" : "") +
      " (desde o " + run.inicio + ")";
  }

  /* ---------------- Previsão do próximo início ---------------- */
  function renderPrevisao(md) {
    var box = el("ordem-previsao");
    if (!md || !md.previsao) {
      box.innerHTML = '<div class="ordem-vazio">Sem dados de histórico.</div>';
      return;
    }
    var prev = md.previsao;
    var probs = prev.probabilidades || {};
    var html = '<div class="ordem-candidatas-lista">';
    (prev.top3_proximo_inicio || []).forEach(function (d, i) {
      var p = probs[String(d)] || 0;
      html += '<div class="ordem-candidata' + (i === 0 ? " lider" : "") + '">' +
        '<div class="ordem-dezena">' + String(d).padStart(2, "0") + "</div>" +
        '<div class="ordem-candidata-info">' +
        '<div class="ordem-candidata-rotulo">' +
        (i === 0 ? "mais provável" : i + "º mais provável") + "</div>" +
        bar(p) +
        '<div class="ordem-candidata-pct">' + fmtPct(p) + "</div></div></div>";
    });
    html += "</div>";

    var regra = prev.regra_do_usuario || {};
    var med = (regra.p_repetir_o_atual || {}).medida_historica;
    if (regra.excluida && med) {
      html += '<div class="ordem-repeticao-box">' +
        '<i class="fas fa-repeat"></i> P(<strong>' +
        String(regra.excluida).padStart(2, "0") + "</strong> abrir de novo, " +
        "após " + regra.streak_atual + "× seguidas): <strong>" +
        fmtPct(med.taxa_real) + "</strong> medido (" + med.provas +
        " provas) · " + fmtPct(med.taxa_teorica) + " teórico" +
        '<div class="ordem-micro">' + (med.leitura || "") + "</div></div>";
    }
    if (regra.candidatas_restantes_top2) {
      html += '<div class="ordem-micro">Regra de exclusão (sua lógica): ' +
        "excluir a atual aponta para " +
        regra.candidatas_restantes_top2.map(function (d) {
          return String(d).padStart(2, "0");
        }).join(" ou ") +
        " — veja o placar ao lado antes de aplicá-la.</div>";
    }
    box.innerHTML = html;
  }

  /* ---------------- Placar das regras ---------------- */
  function renderPlacar(md) {
    var box = el("ordem-placar");
    var pl = md && md.placar_walkforward;
    if (!pl || pl.aplicavel === false) {
      box.innerHTML = '<div class="ordem-vazio">Histórico insuficiente.</div>';
      return;
    }
    var linhas = [
      { rotulo: "Sempre prever 01", d: pl.sempre_01, teto: pl.sempre_01.teto_teorico },
      { rotulo: "Prever {01, 02}", d: pl.top2, teto: pl.top2.teto_teorico },
      { rotulo: "Excluir a atual (sequência ≥ 2)", d: pl.regra_usuario, teto: pl.sempre_01.teto_teorico }
    ];
    var html = "<div>";
    linhas.forEach(function (l) {
      var melhor = l.teto ? l.d.taxa >= l.teto : l.d.taxa > 0;
      html += '<div class="ordem-placar-linha">' +
        '<div class="ordem-placar-rotulo">' + l.rotulo + "</div>" +
        bar(l.d.taxa, melhor ? "verde" : "") +
        '<div class="ordem-placar-nums"><strong>' + fmtPct(l.d.taxa) +
        "</strong> · teto " + fmtPct(l.teto) +
        " · " + l.d.acertos.toLocaleString("pt-BR") + " acertos</div></div>";
    });
    html += "</div>";
    box.innerHTML = html;
  }

  /* ---------------- Streaks ---------------- */
  function renderStreaks(md) {
    var box = el("ordem-streaks");
    var st = md && md.streaks;
    if (!st) {
      box.innerHTML = '<div class="ordem-vazio">Sem dados.</div>';
      return;
    }
    var mx = st.streak_maximo_historico;
    var run = st.run_atual;
    var html = '<div class="ordem-streak-cards">' +
      '<div class="ordem-streak-card recorde"><div class="ordem-streak-num">' +
      (mx ? "0" + mx.dezena : "—") + "</div><div>recorde de aberturas seguidas" +
      (mx ? " — " + mx.comprimento + "× (concursos " + mx.inicio + "–" + mx.fim + ")" : "") +
      "</div></div>" +
      '<div class="ordem-streak-card"><div class="ordem-streak-num">' +
      (run ? "0" + run.dezena : "—") + "</div><div>abertura atual" +
      (run ? " — " + run.comprimento + "× desde o " + run.inicio : "") +
      "</div></div></div>";

    var por = st.por_dezena || {};
    var linhas = Object.keys(por).map(Number)
      .filter(function (d) { return por[d].maximo > 0; })
      .sort(function (a, b) { return por[b].maximo - por[a].maximo; })
      .slice(0, 6);
    if (linhas.length) {
      html += '<table class="ordem-tabela"><thead><tr>' +
        "<th>Dezena</th><th>Recorde</th><th>Janela do recorde</th>" +
        "<th>Última abertura</th></tr></thead><tbody>";
      linhas.forEach(function (d) {
        var info = por[d];
        html += "<tr><td><strong>" + String(d).padStart(2, "0") + "</strong></td>" +
          "<td>" + info.maximo + "× seguidas</td>" +
          "<td>" + info.maximo_inicio + "–" + info.maximo_fim + "</td>" +
          "<td>" + (info.ultimo_concurso || "—") + "</td></tr>";
      });
      html += "</tbody></table>";
    }
    box.innerHTML = html;
  }

  /* ---------------- Frequências ---------------- */
  function renderFrequencias(md) {
    var box = el("ordem-frequencias");
    var f = md && md.frequencias;
    if (!f || !f.tabela) {
      box.innerHTML = '<div class="ordem-vazio">Sem dados.</div>';
      return;
    }
    var maxP = Math.max.apply(null, f.tabela.map(function (r) {
      return Math.max(r.frequencia, r.teorico);
    }).concat([0.01]));
    var html = "";
    f.tabela.slice(0, 8).forEach(function (r) {
      html += '<div class="ordem-freq-linha">' +
        '<div class="ordem-freq-dezena">' + String(r.dezena).padStart(2, "0") + "</div>" +
        '<div class="ordem-freq-bars">' +
        bar(r.frequencia / maxP, "roxo") +
        bar(r.teorico / maxP, "tracejado") + "</div>" +
        '<div class="ordem-freq-nums">' + fmtPct(r.frequencia) +
        ' <span class="ordem-micro">(teo ' + fmtPct(r.teorico) + ")</span></div></div>";
    });
    box.innerHTML = html;
  }

  /* ---------------- Auto-auditoria ---------------- */
  function renderAuditoria(md, ordemReal) {
    var box = el("ordem-auditoria");
    var partes = [];
    var a = md && md.auto_auditoria;
    if (a && a.aplicavel) {
      partes.push('<div class="ordem-aud-card"><h4>Menor dezena (aberturas)</h4>' +
        vereditoBadge(a.veredito) +
        '<div class="ordem-aud-nums">preditor acerta ' + fmtPct(a.taxa) +
        " · teto " + fmtPct(a.teto_teorico) + " · lift " +
        String(a.lift).replace(".", ",") + " · p = " +
        String(a.p_valor).replace(".", ",") + "</div></div>");
    } else if (a) {
      partes.push('<div class="ordem-aud-card"><h4>Menor dezena (aberturas)</h4>' +
        '<span class="ordem-veredito neutro"><i class="fas fa-hourglass-half"></i> dados insuficientes</span></div>');
    }
    var b = ordemReal && ordemReal.auto_auditoria;
    if (b && b.aplicavel) {
      partes.push('<div class="ordem-aud-card"><h4>1ª bola física (ordem real)</h4>' +
        vereditoBadge(b.veredito) +
        '<div class="ordem-aud-nums">top-5 acerta ' + fmtPct(b.taxa_top5) +
        " · acaso " + fmtPct(b.taxa_acaso) + " · lift " +
        String(b.lift).replace(".", ",") + " · p = " +
        String(b.p_valor).replace(".", ",") + "</div></div>");
    } else {
      partes.push('<div class="ordem-aud-card"><h4>1ª bola física (ordem real)</h4>' +
        '<span class="ordem-veredito neutro"><i class="fas fa-hourglass-half"></i> aguardando backfill (≥ 31 concursos)</span></div>');
    }
    box.innerHTML = '<div class="ordem-aud-grid">' + partes.join("") + "</div>";
  }

  /* ---------------- Ordem real (1ª bola) ---------------- */
  function renderOrdemReal(or) {
    var box = el("ordem-real");
    if (!or || or.status === "erro") {
      box.innerHTML = '<div class="ordem-vazio">Indisponível.</div>';
      return;
    }
    if (!or.n_registros || or.n_registros < 30) {
      box.innerHTML = '<div class="ordem-backfill">' +
        '<i class="fas fa-satellite-dish"></i> A ordem física de extração ' +
        "(1ª, 2ª, … bola) ainda não estava no histórico — o sistema já a " +
        "captura automaticamente dos novos concursos. Para o histórico " +
        "completo, rode na sua máquina:<code>python backfill_ordem.py</code>" +
        '<div class="ordem-micro">Registros atuais: ' + (or.n_registros || 0) +
        " (ex.: no 3769 a 1ª bola foi 09 e a 03 saiu como 13ª bola).</div></div>";
      return;
    }
    var prev = or.previsao || {};
    var trio = prev.trio_01_02_03 || {};
    var taxa = or.taxa_repeticao || {};
    var html = '<div class="ordem-real-grid">';

    html += '<div><h4>Trio 01 · 02 · 03 como 1ª bola física</h4>';
    ["1", "2", "3"].forEach(function (d) {
      var t = trio[d] || {};
      html += '<div class="ordem-freq-linha">' +
        '<div class="ordem-freq-dezena">0' + d + "</div>" +
        '<div class="ordem-freq-bars">' + bar(t.prob_primeira_bola || 0) + "</div>" +
        '<div class="ordem-freq-nums">' + fmtPct(t.prob_primeira_bola, 2) +
        ' <span class="ordem-micro">(streak ' + (t.streak_atual || 0) +
        " · máx " + (t.maximo_historico || 0) + ")</span></div></div>";
    });
    html += "</div>";

    html += "<div><h4>Repetição da 1ª bola</h4>";
    if (taxa.global) {
      html += '<div class="ordem-aud-nums">global: ' + fmtPct(taxa.global.taxa) +
        " vs acaso " + fmtPct(taxa.global.taxa_acaso) +
        " (p = " + String(taxa.global.p_valor).replace(".", ",") + ")</div>";
    }
    var pl = or.placar_regra_exclusao;
    if (pl && pl.aplicavel) {
      html += '<div class="ordem-aud-nums">regra "a última não repete": ' +
        fmtPct(pl.taxa_real) + " voltou (" + pl.voltou + "/" + pl.n_transicoes +
        ") → " + vereditoBadge(pl.veredito.indexOf("SUPORTADO") === 0 ? "REAL" : "RUÍDO") + "</div>";
    }
    html += "</div></div>";
    box.innerHTML = html;
  }

  /* ---------------- Boot ---------------- */
  fetch("/api/magna/ordem")
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var md = d.menor_dezena && d.menor_dezena.status === "ok"
        ? d.menor_dezena : null;
      renderRunAtual(md);
      renderPrevisao(md);
      renderPlacar(md);
      renderStreaks(md);
      renderFrequencias(md);
      renderAuditoria(md, d);
      renderOrdemReal(d);
    })
    .catch(function () {
      ["ordem-previsao", "ordem-placar", "ordem-streaks",
       "ordem-frequencias", "ordem-auditoria", "ordem-real"]
        .forEach(function (id) {
          var b = el(id);
          if (b) b.innerHTML =
            '<div class="ordem-vazio">Falha ao consultar /api/magna/ordem.</div>';
        });
    });
})();
