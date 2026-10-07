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
        } catch (e) {  }
    }

    document.addEventListener("ct:cookies", function () {
        if (permitido()) return;
        gravar([]);
        var secao = document.querySelector("[data-vistos]");
        if (secao) secao.hidden = true;
    });

    var visto = script && script.dataset.vistoId;
    if (visto) {
        if (!permitido()) return;
        var lista = ler().filter(function (id) { return String(id) !== visto; });
        lista.unshift(Number(visto));
        gravar(lista.slice(0, LIMITE));
        return;
    }

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
            .catch(function () {  });

        secao.querySelector("[data-vistos-limpar]").addEventListener("click", function () {
            gravar([]);
            secao.hidden = true;
            var proximo = secao.nextElementSibling && secao.nextElementSibling.querySelector("h2");
            if (proximo) {
                proximo.setAttribute("tabindex", "-1");
                proximo.focus();
            }
        });
    });
})();
