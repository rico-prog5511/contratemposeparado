/* =====================================================================
   TESTE — escolher o efeito de seleção dos cards do site (produtos,
   categorias, faixas de preço, guia, resumo da conta, opções do checkout).

   Abra qualquer página com ?testar-selecao no endereço: aparece uma caixa
   para trocar entre as opções (ver css/teste-selecao.css). A escolha fica
   salva NESTE navegador, então dá para navegar pelo site todo com ela.
   "Encerrar teste" apaga tudo. Quem não abriu com ?testar-selecao não vê
   nada disso. Carregado em base.html (linhas marcadas com TESTE).
   ===================================================================== */
(function () {
    "use strict";

    var CHAVE = "ct-teste-selecao";
    var CHAVE_MIN = "ct-teste-selecao-min";
    var OPCOES = [
        "0. Atual (sobe com sombra azul)",
        "1. Moldura vermelha",
        "2. Barra lateral",
        "3. Elevação suave",
        "4. Cores invertidas",
        "5. Seta que entra"
    ];

    function lerChave(chave) { try { return localStorage.getItem(chave); } catch (e) { return null; } }
    function gravarChave(chave, v) {
        try { if (v === null) localStorage.removeItem(chave); else localStorage.setItem(chave, v); } catch (e) { /* sem localStorage: só nesta página */ }
    }
    function ler() { return lerChave(CHAVE); }
    function gravar(v) { gravarChave(CHAVE, v); }

    var escolha = ler();
    if (escolha === null && /[?&]testar-selecao\b/.test(location.search)) escolha = "0";
    if (escolha === null) return;

    var raiz = document.documentElement;
    function aplicar(valor) {
        escolha = valor;
        gravar(valor);
        if (valor === "0") raiz.removeAttribute("data-selecao");
        else raiz.setAttribute("data-selecao", valor);
    }
    aplicar(escolha);

    document.addEventListener("DOMContentLoaded", function () {
        var barra = document.createElement("section");
        barra.className = "teste-selecao";
        barra.setAttribute("aria-labelledby", "teste-selecao-titulo");
        barra.innerHTML =
            '<h2 id="teste-selecao-titulo">Teste: efeito de seleção</h2>' +
            "<p>Passe o mouse (ou use Tab) nos cards: produtos, categorias, faixas de preço, guia, conta e checkout.</p>" +
            "<ol></ol>" +
            '<div class="teste-selecao-acoes">' +
            '<button type="button" class="link-button teste-selecao-min" aria-expanded="true">Minimizar</button>' +
            '<button type="button" class="link-button teste-selecao-sair">Encerrar teste</button>' +
            "</div>";
        var lista = barra.querySelector("ol");
        var minimizar = barra.querySelector(".teste-selecao-min");

        function aplicarMinimizada(min) {
            barra.classList.toggle("minimizada", min);
            minimizar.textContent = min ? "Mostrar opções" : "Minimizar";
            minimizar.setAttribute("aria-expanded", String(!min));
            gravarChave(CHAVE_MIN, min ? "1" : null);
        }
        minimizar.addEventListener("click", function () { aplicarMinimizada(!barra.classList.contains("minimizada")); });
        aplicarMinimizada(lerChave(CHAVE_MIN) === "1");

        OPCOES.forEach(function (rotulo, i) {
            var item = document.createElement("li");
            var botao = document.createElement("button");
            botao.type = "button";
            botao.textContent = rotulo;
            botao.setAttribute("aria-pressed", String(String(i) === escolha));
            botao.addEventListener("click", function () {
                aplicar(String(i));
                lista.querySelectorAll("button").forEach(function (b, j) { b.setAttribute("aria-pressed", String(j === i)); });
            });
            item.appendChild(botao);
            lista.appendChild(item);
        });

        barra.querySelector(".teste-selecao-sair").addEventListener("click", function () {
            gravar(null);
            gravarChave(CHAVE_MIN, null);
            raiz.removeAttribute("data-selecao");
            barra.remove();
        });
        document.body.appendChild(barra);
    });
})();
