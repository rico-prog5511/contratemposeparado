document.addEventListener("DOMContentLoaded", function () {
    var painel = document.querySelector("[data-filters]");
    if (!painel) return;

    var temFiltros = painel.querySelector(".tab-count") !== null;
    var telaPequena = window.matchMedia("(max-width: 860px)");

    function ajustar() {
        if (telaPequena.matches && !temFiltros) {
            painel.removeAttribute("open");
        } else if (!telaPequena.matches) {
            painel.setAttribute("open", "");
        }
    }

    ajustar();
    telaPequena.addEventListener("change", ajustar);

    function semAcento(texto) {
        return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }
    painel.querySelectorAll("[data-filtro-busca]").forEach(function (campo) {
        var grupo = campo.closest(".filter-group");
        campo.hidden = false;
        campo.addEventListener("input", function () {
            var termo = semAcento(campo.value.trim());
            grupo.querySelectorAll("[data-filtro-item]").forEach(function (item) {
                var marcado = item.querySelector("input").checked;
                item.hidden = termo !== "" && !marcado && semAcento(item.dataset.filtroItem).indexOf(termo) === -1;
            });
        });
    });
});
