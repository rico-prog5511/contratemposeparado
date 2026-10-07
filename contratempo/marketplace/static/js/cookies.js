(function () {
    "use strict";

    var NOME = "ct_cookies";
    var VERSAO = "1";
    var DURACAO = 365 * 24 * 60 * 60;

    function ler() {
        var achado = document.cookie.split("; ").filter(function (c) { return c.indexOf(NOME + "=") === 0; })[0];
        if (!achado) return null;
        var valores = {};
        decodeURIComponent(achado.slice(NOME.length + 1)).split("&").forEach(function (par) {
            var partes = par.split("=");
            valores[partes[0]] = partes[1];
        });
        return valores.v === VERSAO ? valores : null;
    }

    function salvar(funcionais) {
        var valor = "v=" + VERSAO + "&funcionais=" + (funcionais ? "1" : "0") + "&data=" + new Date().toISOString().slice(0, 10);
        var seguro = location.protocol === "https:" ? "; Secure" : "";
        document.cookie = NOME + "=" + encodeURIComponent(valor) + "; Max-Age=" + DURACAO + "; Path=/; SameSite=Lax" + seguro;
        document.dispatchEvent(new CustomEvent("ct:cookies", { detail: { funcionais: funcionais } }));
    }

    window.ctCookies = {
        escolhido: function () { return ler() !== null; },
        permitido: function (categoria) {
            if (categoria === "essenciais") return true;
            var escolha = ler();
            return !!escolha && escolha[categoria] === "1";
        },
        salvar: salvar
    };

    document.addEventListener("DOMContentLoaded", function () {
        var aviso = document.getElementById("cookie-aviso");
        var dialogo = document.getElementById("cookie-preferencias");
        if (!aviso || !dialogo) return;
        var caixaFuncionais = dialogo.querySelector("[name='funcionais']");
        var raiz = document.documentElement;

        function ajustarEspaco() {
            raiz.style.setProperty("--cookie-aviso-altura", aviso.hidden ? "0px" : aviso.offsetHeight + "px");
        }

        function mostrarAviso(mostrar) {
            aviso.hidden = !mostrar;
            ajustarEspaco();
        }

        function escolher(funcionais) {
            salvar(funcionais);
            mostrarAviso(false);
        }

        function abrirPreferencias() {
            caixaFuncionais.checked = window.ctCookies.permitido("funcionais");
            dialogo.showModal();
        }

        mostrarAviso(!window.ctCookies.escolhido());
        if (window.ResizeObserver) new ResizeObserver(ajustarEspaco).observe(aviso);
        else window.addEventListener("resize", ajustarEspaco);

        aviso.querySelector("[data-cookies-aceitar]").addEventListener("click", function () { escolher(true); });
        aviso.querySelector("[data-cookies-recusar]").addEventListener("click", function () { escolher(false); });
        document.querySelectorAll("[data-cookies-abrir]").forEach(function (botao) {
            botao.hidden = false;
            botao.addEventListener("click", abrirPreferencias);
        });

        dialogo.addEventListener("close", function () {
            if (dialogo.returnValue === "salvar") escolher(caixaFuncionais.checked);
            else if (dialogo.returnValue === "todos") escolher(true);
        });
    });
})();
