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

    /* Campo "Procurar…" nas listas longas (marcas): esconde as opções que não batem. */
    function semAcento(texto) {
        return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }
    painel.querySelectorAll("[data-filtro-busca]").forEach(function (campo) {
        var grupo = campo.closest(".filter-group");
        campo.hidden = false;  // sem JavaScript o campo não teria função
        campo.addEventListener("input", function () {
            var termo = semAcento(campo.value.trim());
            grupo.querySelectorAll("[data-filtro-item]").forEach(function (item) {
                var marcado = item.querySelector("input").checked;
                item.hidden = termo !== "" && !marcado && semAcento(item.dataset.filtroItem).indexOf(termo) === -1;
            });
        });
    });
});
