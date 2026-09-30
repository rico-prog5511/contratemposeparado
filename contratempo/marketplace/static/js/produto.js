/* static/js/produto.js — específico da página de detalhe do produto
 *
 *   - miniaturas trocam a imagem principal (setas do teclado navegam)
 *   - clicar na imagem principal abre a galeria ampliada (lightbox):
 *     setas ← →, deslizar no celular, Esc ou clique fora para fechar
 *   - botões +/- da quantidade
 */

document.addEventListener("DOMContentLoaded", function () {
    var imagemPrincipal = document.getElementById("imagem-principal");
    var miniaturas = document.querySelectorAll(".produto-miniatura");

    /* ---------------------------------------------------------------
       MINIATURAS
       --------------------------------------------------------------- */
    function mostrarNaPrincipal(indice) {
        var miniatura = miniaturas[indice];
        if (!imagemPrincipal || !miniatura) return;
        imagemPrincipal.src = miniatura.getAttribute("data-src");
        imagemPrincipal.dataset.indice = String(indice);
        miniaturas.forEach(function (m) {
            m.classList.remove("active");
            m.removeAttribute("aria-current");
        });
        miniatura.classList.add("active");
        miniatura.setAttribute("aria-current", "true");
    }

    miniaturas.forEach(function (miniatura, indice) {
        miniatura.addEventListener("click", function () { mostrarNaPrincipal(indice); });

        miniatura.addEventListener("keydown", function (e) {
            var alvo = null;
            if (e.key === "ArrowDown" || e.key === "ArrowRight") alvo = indice + 1;
            if (e.key === "ArrowUp" || e.key === "ArrowLeft") alvo = indice - 1;
            if (alvo !== null && miniaturas[alvo]) {
                e.preventDefault();
                miniaturas[alvo].focus();
                mostrarNaPrincipal(alvo);
            }
        });
    });

    /* ---------------------------------------------------------------
       LIGHTBOX
       --------------------------------------------------------------- */
    var lightbox = document.getElementById("lightbox");
    var dados = document.getElementById("lightbox-dados");
    var abrir = document.querySelector("[data-lightbox-open]");

    if (lightbox && dados && abrir && typeof lightbox.showModal === "function") {
        var imagens = JSON.parse(dados.textContent);
        var imgGrande = document.getElementById("lightbox-img");
        var posicao = document.getElementById("lightbox-pos");
        var atual = 0;

        function mostrar(indice) {
            atual = (indice + imagens.length) % imagens.length;
            imgGrande.src = imagens[atual];
            posicao.textContent = String(atual + 1);
        }

        abrir.addEventListener("click", function () {
            mostrar(parseInt(imagemPrincipal.dataset.indice || "0", 10));
            lightbox.showModal();
        });

        lightbox.querySelector("[data-lightbox-close]").addEventListener("click", function () { lightbox.close(); });
        var anterior = lightbox.querySelector("[data-lightbox-prev]");
        var proxima = lightbox.querySelector("[data-lightbox-next]");
        if (anterior) anterior.addEventListener("click", function () { mostrar(atual - 1); });
        if (proxima) proxima.addEventListener("click", function () { mostrar(atual + 1); });

        // Clique no fundo escuro (fora da imagem) fecha
        lightbox.addEventListener("click", function (e) {
            if (e.target === lightbox) lightbox.close();
        });

        lightbox.addEventListener("keydown", function (e) {
            if (imagens.length < 2) return;
            if (e.key === "ArrowRight") mostrar(atual + 1);
            if (e.key === "ArrowLeft") mostrar(atual - 1);
        });

        // Deslizar no celular
        var inicioX = null;
        lightbox.addEventListener("touchstart", function (e) { inicioX = e.touches[0].clientX; }, { passive: true });
        lightbox.addEventListener("touchend", function (e) {
            if (inicioX === null || imagens.length < 2) return;
            var delta = e.changedTouches[0].clientX - inicioX;
            if (Math.abs(delta) > 50) mostrar(delta < 0 ? atual + 1 : atual - 1);
            inicioX = null;
        });

        // Ao fechar, a imagem principal acompanha a última vista
        lightbox.addEventListener("close", function () {
            if (miniaturas.length) mostrarNaPrincipal(atual);
        });
    }

    /* ---------------------------------------------------------------
       QUANTIDADE
       --------------------------------------------------------------- */
    var input = document.getElementById("quantidade");
    if (input) {
        var limitar = function (valor) {
            var max = parseInt(input.max || "999", 10);
            var min = parseInt(input.min || "1", 10);
            if (isNaN(valor)) valor = min;
            return Math.max(min, Math.min(max, valor));
        };

        document.querySelectorAll(".qtd-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var valor = parseInt(input.value || "1", 10);
                valor = btn.dataset.acao === "mais" ? valor + 1 : valor - 1;
                input.value = limitar(valor);
            });
        });

        input.addEventListener("change", function () {
            input.value = limitar(parseInt(input.value, 10));
        });
    }
});
