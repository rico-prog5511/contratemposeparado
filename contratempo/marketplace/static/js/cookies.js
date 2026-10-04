/* =====================================================================
   cookies.js — aviso e preferências de cookies (LGPD).

   Categorias:
     essenciais  sempre ligados: login (sessionid), segurança dos
                 formulários (csrftoken), avisos (messages), esta própria
                 escolha (ct_cookies) e as preferências de acessibilidade.
     funcionais  opcionais: "Vistos recentemente" (vistos.js).

   A escolha fica no cookie "ct_cookies" por 12 meses; depois o aviso
   volta. Enquanto a pessoa não escolhe, os opcionais ficam DESLIGADOS.

   Outros scripts perguntam com window.ctCookies.permitido("funcionais")
   e escutam o evento "ct:cookies" para reagir a mudanças.
   Carregado no <head> (antes dos outros scripts).
   ===================================================================== */
(function () {
    "use strict";

    var NOME = "ct_cookies";
    var VERSAO = "1";            // mude para pedir o consentimento de novo (ex.: categoria nova)
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

        // O aviso fica preso no rodapé da tela: os botões flutuantes sobem para não ficar embaixo dele.
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
        // A altura do aviso muda quando as fontes terminam de carregar ou a tela gira.
        if (window.ResizeObserver) new ResizeObserver(ajustarEspaco).observe(aviso);
        else window.addEventListener("resize", ajustarEspaco);

        aviso.querySelector("[data-cookies-aceitar]").addEventListener("click", function () { escolher(true); });
        aviso.querySelector("[data-cookies-recusar]").addEventListener("click", function () { escolher(false); });
        document.querySelectorAll("[data-cookies-abrir]").forEach(function (botao) {
            botao.hidden = false;  // sem JavaScript o botão não teria função
            botao.addEventListener("click", abrirPreferencias);
        });

        dialogo.addEventListener("close", function () {
            if (dialogo.returnValue === "salvar") escolher(caixaFuncionais.checked);
            else if (dialogo.returnValue === "todos") escolher(true);
        });
    });
})();
