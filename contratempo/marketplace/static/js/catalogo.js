/* static/js/catalogo.js — página de produtos/busca
 * Em telas pequenas o painel de filtros começa recolhido (a menos que
 * haja filtros aplicados), para os produtos aparecerem primeiro.
 */

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
});
