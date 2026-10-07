document.addEventListener("DOMContentLoaded", function () {
    var carrossel = document.querySelector("[data-carrossel]");
    if (!carrossel) return;

    var slides = carrossel.querySelectorAll(".carrossel-slide");
    var controles = carrossel.querySelector(".carrossel-controles");
    var trilho = carrossel.querySelector(".carrossel-trilho");
    var botaoPausa = carrossel.querySelector("[data-pausa]");
    if (slides.length < 2) return;

    carrossel.setAttribute("aria-roledescription", "carrossel");
    var grupoPontos = carrossel.querySelector(".carrossel-pontos");
    slides.forEach(function (slide, i) {
        slide.setAttribute("aria-roledescription", "slide");
        slide.setAttribute("aria-label", (i + 1) + " de " + slides.length);
        var ponto = document.createElement("button");
        ponto.type = "button";
        ponto.className = "carrossel-ponto";
        ponto.setAttribute("aria-label", "Slide " + (i + 1));
        grupoPontos.appendChild(ponto);
    });
    var pontos = grupoPontos.querySelectorAll(".carrossel-ponto");

    var INTERVALO = 7000;
    var atual = 0;
    var timer = null;
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
        trilho.setAttribute("aria-live", pausadoPeloUsuario ? "polite" : "off");
    }

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

    carrossel.addEventListener("mouseenter", function () { emInteracao = true; parar(); });
    carrossel.addEventListener("mouseleave", function () { emInteracao = false; iniciar(); });
    carrossel.addEventListener("focusin", function () { emInteracao = true; parar(); });
    carrossel.addEventListener("focusout", function (e) {
        if (!carrossel.contains(e.relatedTarget)) { emInteracao = false; iniciar(); }
    });

    carrossel.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") { e.preventDefault(); irPara(atual - 1); }
        if (e.key === "ArrowRight") { e.preventDefault(); irPara(atual + 1); }
    });

    var inicioX = null;
    carrossel.addEventListener("touchstart", function (e) { inicioX = e.touches[0].clientX; }, { passive: true });
    carrossel.addEventListener("touchend", function (e) {
        if (inicioX === null) return;
        var delta = e.changedTouches[0].clientX - inicioX;
        if (Math.abs(delta) > 50) irPara(delta < 0 ? atual + 1 : atual - 1);
        inicioX = null;
    });

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) parar(); else iniciar();
    });

    document.addEventListener("ct:acessibilidade", function () {
        pausadoPeloUsuario = animacoesPausadas();
        atualizarBotaoPausa();
        iniciar();
    });

    mostrar(0);
    atualizarBotaoPausa();
    iniciar();
});
