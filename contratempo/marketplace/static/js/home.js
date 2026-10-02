/* static/js/home.js — carrossel do banner da página inicial
 *
 *   - troca de slide a cada 7 s (para quando o mouse ou o foco está no
 *     banner, ou se o usuário pediu "menos movimento" no sistema);
 *   - setas, pontos, botão de pausar, setas do teclado e deslizar no
 *     celular;
 *   - sem JavaScript, o primeiro slide fica fixo (nada quebra).
 */

document.addEventListener("DOMContentLoaded", function () {
    var carrossel = document.querySelector("[data-carrossel]");
    if (!carrossel) return;

    var slides = carrossel.querySelectorAll(".carrossel-slide");
    var pontos = carrossel.querySelectorAll(".carrossel-ponto");
    var controles = carrossel.querySelector(".carrossel-controles");
    var trilho = carrossel.querySelector(".carrossel-trilho");
    var botaoPausa = carrossel.querySelector("[data-pausa]");
    if (slides.length < 2) return;

    var INTERVALO = 7000;
    var atual = 0;
    var timer = null;
    // Para sozinho se o sistema pede "menos movimento" ou se a pessoa
    // ligou "Pausar animações" no painel de acessibilidade.
    var animacoesPausadas = function () { return document.documentElement.dataset.animacoes === "pausar"; };
    var pausadoPeloUsuario = window.matchMedia("(prefers-reduced-motion: reduce)").matches || animacoesPausadas();
    var emInteracao = false;

    controles.hidden = false;

    function mostrar(indice) {
        atual = (indice + slides.length) % slides.length;
        slides.forEach(function (slide, i) {
            var ativo = i === atual;
            slide.classList.toggle("ativo", ativo);
            slide.setAttribute("aria-hidden", ativo ? "false" : "true");
            // Links de slides escondidos não recebem foco pelo Tab
            slide.querySelectorAll("a, button").forEach(function (el) {
                el.tabIndex = ativo ? 0 : -1;
            });
        });
        pontos.forEach(function (ponto, i) {
            ponto.classList.toggle("ativo", i === atual);
            if (i === atual) ponto.setAttribute("aria-current", "true");
            else ponto.removeAttribute("aria-current");
        });
    }

    function parar() { clearInterval(timer); timer = null; }
    function iniciar() {
        parar();
        if (pausadoPeloUsuario || emInteracao) return;
        timer = setInterval(function () { mostrar(atual + 1); }, INTERVALO);
    }

    function atualizarBotaoPausa() {
        botaoPausa.textContent = pausadoPeloUsuario ? "▶" : "❚❚";
        botaoPausa.setAttribute("aria-label", pausadoPeloUsuario ? "Retomar a troca automática" : "Pausar a troca automática");
        // Quando a troca é manual, avisa o leitor de tela a cada mudança
        trilho.setAttribute("aria-live", pausadoPeloUsuario ? "polite" : "off");
    }

    // Navegação manual reinicia a contagem
    function irPara(indice) { mostrar(indice); iniciar(); }

    carrossel.querySelector("[data-anterior]").addEventListener("click", function () { irPara(atual - 1); });
    carrossel.querySelector("[data-proximo]").addEventListener("click", function () { irPara(atual + 1); });
    pontos.forEach(function (ponto, i) {
        ponto.addEventListener("click", function () { irPara(i); });
    });
    botaoPausa.addEventListener("click", function () {
        pausadoPeloUsuario = !pausadoPeloUsuario;
        atualizarBotaoPausa();
        iniciar();
    });

    // Pausa enquanto o mouse ou o foco do teclado estão no banner
    carrossel.addEventListener("mouseenter", function () { emInteracao = true; parar(); });
    carrossel.addEventListener("mouseleave", function () { emInteracao = false; iniciar(); });
    carrossel.addEventListener("focusin", function () { emInteracao = true; parar(); });
    carrossel.addEventListener("focusout", function (e) {
        if (!carrossel.contains(e.relatedTarget)) { emInteracao = false; iniciar(); }
    });

    // Setas do teclado
    carrossel.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") { e.preventDefault(); irPara(atual - 1); }
        if (e.key === "ArrowRight") { e.preventDefault(); irPara(atual + 1); }
    });

    // Deslizar no celular
    var inicioX = null;
    carrossel.addEventListener("touchstart", function (e) { inicioX = e.touches[0].clientX; }, { passive: true });
    carrossel.addEventListener("touchend", function (e) {
        if (inicioX === null) return;
        var delta = e.changedTouches[0].clientX - inicioX;
        if (Math.abs(delta) > 50) irPara(delta < 0 ? atual + 1 : atual - 1);
        inicioX = null;
    });

    // Não troca de slide com a aba do navegador escondida
    document.addEventListener("visibilitychange", function () {
        if (document.hidden) parar(); else iniciar();
    });

    // Painel de acessibilidade ligou/desligou "Pausar animações"
    document.addEventListener("ct:acessibilidade", function () {
        pausadoPeloUsuario = animacoesPausadas();
        atualizarBotaoPausa();
        iniciar();
    });

    mostrar(0);
    atualizarBotaoPausa();
    iniciar();
});
