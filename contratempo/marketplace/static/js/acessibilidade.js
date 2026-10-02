/* static/js/acessibilidade.js — painel de acessibilidade
 *
 * As escolhas ficam no localStorage ("ct-acessibilidade") e viram
 * atributos no <html>, que o acessibilidade.css usa:
 *   data-texto="-1..4"          tamanho do texto
 *   data-tema="escuro"          tema escuro (também quando "Do sistema" e o sistema está escuro)
 *   data-contraste="alto"       alto contraste
 *   data-leitura="facil"        fonte Atkinson Hyperlegible (dislexia/baixa visão)
 *   data-links="destacar"       links sublinhados e em negrito
 *   data-espacamento="amplo"    mais espaço entre linhas, letras e palavras
 *   data-animacoes="pausar"     sem animações (o carrossel da home para)
 *
 * Um trecho curto em base.html aplica as escolhas ANTES da página
 * aparecer (sem "piscar"); este arquivo cuida do painel.
 */

(function () {
    var CHAVE = "ct-acessibilidade";
    var PADRAO = { texto: 0, tema: "claro", contraste: false, leitura: false, links: false, espacamento: false, animacoes: false };
    var raiz = document.documentElement;
    var sistemaEscuro = window.matchMedia("(prefers-color-scheme: dark)");

    function ler() {
        try {
            var salvo = JSON.parse(localStorage.getItem(CHAVE) || "{}");
            var p = {};
            for (var k in PADRAO) p[k] = (k in salvo) ? salvo[k] : PADRAO[k];
            return p;
        } catch (e) {
            return Object.assign({}, PADRAO);
        }
    }

    function salvar(p) {
        try { localStorage.setItem(CHAVE, JSON.stringify(p)); } catch (e) { /* modo privado: só vale nesta página */ }
    }

    function carregarFonteLeitura() {
        if (document.getElementById("fonte-leitura-facil")) return;
        var link = document.createElement("link");
        link.id = "fonte-leitura-facil";
        link.rel = "stylesheet";
        link.href = "https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&display=swap";
        document.head.appendChild(link);
    }

    function atributo(nome, ativo, valor) {
        if (ativo) raiz.setAttribute(nome, valor);
        else raiz.removeAttribute(nome);
    }

    function aplicar(p) {
        atributo("data-texto", p.texto !== 0, String(p.texto));
        var escuro = p.tema === "escuro" || (p.tema === "auto" && sistemaEscuro.matches);
        atributo("data-tema", escuro, "escuro");
        atributo("data-contraste", p.contraste, "alto");
        atributo("data-leitura", p.leitura, "facil");
        atributo("data-links", p.links, "destacar");
        atributo("data-espacamento", p.espacamento, "amplo");
        atributo("data-animacoes", p.animacoes, "pausar");
        if (p.leitura) carregarFonteLeitura();
        // Outros scripts (carrossel da home) reagem a esta mudança
        document.dispatchEvent(new CustomEvent("ct:acessibilidade", { detail: p }));
    }

    var prefs = ler();
    aplicar(prefs);
    sistemaEscuro.addEventListener("change", function () { if (prefs.tema === "auto") aplicar(prefs); });

    document.addEventListener("DOMContentLoaded", function () {
        var botao = document.getElementById("acess-botao");
        var painel = document.getElementById("acess-painel");
        var aviso = document.getElementById("acess-aviso");
        var saidaTexto = document.getElementById("acess-texto-valor");
        if (!botao || !painel) return;

        var ROTULOS = {
            contraste: "Alto contraste", leitura: "Fonte para dislexia", links: "Destacar links",
            espacamento: "Mais espaçamento", animacoes: "Pausar animações",
        };
        var TEMAS = { claro: "Tema claro", escuro: "Tema escuro", auto: "Tema do sistema" };

        function anunciar(texto) {
            aviso.textContent = "";
            setTimeout(function () { aviso.textContent = texto; }, 50);
        }

        function atualizarPainel() {
            saidaTexto.textContent = (100 + prefs.texto * 12.5) + "%";
            painel.querySelector('[data-acess-texto="-1"]').disabled = prefs.texto <= -1;
            painel.querySelector('[data-acess-texto="+1"]').disabled = prefs.texto >= 4;
            painel.querySelectorAll("[data-acess-tema]").forEach(function (b) {
                b.setAttribute("aria-pressed", String(b.dataset.acessTema === prefs.tema));
            });
            painel.querySelectorAll("[data-acess-opcao]").forEach(function (b) {
                b.setAttribute("aria-pressed", String(!!prefs[b.dataset.acessOpcao]));
            });
        }

        function mudar(alteracao, mensagem) {
            Object.assign(prefs, alteracao);
            salvar(prefs);
            aplicar(prefs);
            atualizarPainel();
            if (mensagem) anunciar(mensagem);
        }

        function abrir() {
            painel.hidden = false;
            botao.setAttribute("aria-expanded", "true");
            botao.setAttribute("aria-label", "Fechar opções de acessibilidade");
            painel.querySelector("button").focus();
        }
        function fechar(devolverFoco) {
            painel.hidden = true;
            botao.setAttribute("aria-expanded", "false");
            botao.setAttribute("aria-label", "Abrir opções de acessibilidade");
            if (devolverFoco) botao.focus();
        }

        botao.addEventListener("click", function () { painel.hidden ? abrir() : fechar(true); });
        painel.querySelector("[data-acess-fechar]").addEventListener("click", function () { fechar(true); });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && !painel.hidden) fechar(true);
        });
        document.addEventListener("click", function (e) {
            if (!painel.hidden && !painel.contains(e.target) && !botao.contains(e.target)) fechar(false);
        });

        painel.querySelectorAll("[data-acess-texto]").forEach(function (b) {
            b.addEventListener("click", function () {
                var novo = Math.max(-1, Math.min(4, prefs.texto + parseInt(b.dataset.acessTexto, 10)));
                mudar({ texto: novo }, "Texto em " + (100 + novo * 12.5) + "%");
            });
        });
        painel.querySelectorAll("[data-acess-tema]").forEach(function (b) {
            b.addEventListener("click", function () {
                mudar({ tema: b.dataset.acessTema }, TEMAS[b.dataset.acessTema] + " ativado");
            });
        });
        painel.querySelectorAll("[data-acess-opcao]").forEach(function (b) {
            b.addEventListener("click", function () {
                var chave = b.dataset.acessOpcao;
                var alteracao = {};
                alteracao[chave] = !prefs[chave];
                mudar(alteracao, ROTULOS[chave] + (alteracao[chave] ? " ativado" : " desativado"));
            });
        });
        painel.querySelector("[data-acess-restaurar]").addEventListener("click", function () {
            mudar(Object.assign({}, PADRAO), "Configurações de acessibilidade restauradas");
        });

        atualizarPainel();
    });
})();
