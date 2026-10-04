/* =====================================================================
   vistos.js — "Vistos recentemente".

   Na página do produto (<script ... data-visto-id="12">): guarda o id no
   histórico DESTE navegador (localStorage), do mais recente para o mais
   antigo, até 12 produtos. Nada vai para o servidor nem para a conta.

   Na home ([data-vistos]): busca os cards desses produtos em
   /produtos/vistos/?ids=... (só voltam anúncios ainda ativos) e mostra a
   seção. Sem histórico, sem JavaScript ou sem localStorage, a seção
   continua escondida.

   É um recurso "funcional" do aviso de cookies (cookies.js): só grava e
   só mostra se a pessoa aceitou; se ela desligar depois, o histórico é
   apagado na hora.
   ===================================================================== */
(function () {
    "use strict";

    var CHAVE = "ct-vistos";
    var LIMITE = 12;
    var script = document.currentScript;

    function permitido() {
        return !!(window.ctCookies && window.ctCookies.permitido("funcionais"));
    }

    function ler() {
        try {
            var lista = JSON.parse(localStorage.getItem(CHAVE) || "[]");
            return Array.isArray(lista) ? lista.filter(function (id) { return /^\d+$/.test(String(id)); }) : [];
        } catch (e) {
            return [];
        }
    }

    function gravar(lista) {
        try {
            if (lista.length) localStorage.setItem(CHAVE, JSON.stringify(lista));
            else localStorage.removeItem(CHAVE);
        } catch (e) { /* navegador sem localStorage: só não guarda */ }
    }

    // Recusou (ou desligou) os cookies funcionais: apaga o que houver.
    document.addEventListener("ct:cookies", function () {
        if (permitido()) return;
        gravar([]);
        var secao = document.querySelector("[data-vistos]");
        if (secao) secao.hidden = true;
    });

    // Página do produto: registra a visita (só com permissão).
    var visto = script && script.dataset.vistoId;
    if (visto) {
        if (!permitido()) return;
        var lista = ler().filter(function (id) { return String(id) !== visto; });
        lista.unshift(Number(visto));
        gravar(lista.slice(0, LIMITE));
        return;
    }

    // Home: mostra a seção.
    document.addEventListener("DOMContentLoaded", function () {
        var secao = document.querySelector("[data-vistos]");
        if (!secao) return;
        var ids = permitido() ? ler() : [];
        if (!ids.length) return;

        fetch(secao.dataset.url + "?ids=" + ids.join(","), { headers: { "X-Requested-With": "fetch" } })
            .then(function (resposta) { return resposta.ok ? resposta.text() : ""; })
            .then(function (html) {
                if (!html.trim() || !permitido()) return;
                secao.querySelector("[data-vistos-lista]").innerHTML = html;
                secao.hidden = false;
            })
            .catch(function () { /* sem rede: a seção só não aparece */ });

        secao.querySelector("[data-vistos-limpar]").addEventListener("click", function () {
            gravar([]);
            secao.hidden = true;
            // O botão sumiu junto com a seção: o foco vai para a próxima seção.
            var proximo = secao.nextElementSibling && secao.nextElementSibling.querySelector("h2");
            if (proximo) {
                proximo.setAttribute("tabindex", "-1");
                proximo.focus();
            }
        });
    });
})();
