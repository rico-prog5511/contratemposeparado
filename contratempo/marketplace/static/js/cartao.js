(function () {
    "use strict";

    var MASCARAS = {
        cartao: { max: 19, formatar: function (d) { return d.replace(/(\d{4})(?=\d)/g, "$1 "); } },
        validade: { max: 4, formatar: function (d) { return d.length > 2 ? d.slice(0, 2) + "/" + d.slice(2) : d; } },
        cvv: { max: 4, formatar: function (d) { return d; } }
    };

    function aplicarMascara(campo) {
        var mascara = MASCARAS[campo.dataset.mascara];
        if (!mascara) return;
        campo.addEventListener("input", function () {
            var antesDoCursor = campo.value.slice(0, campo.selectionStart).replace(/\D/g, "").length;
            var digitos = campo.value.replace(/\D/g, "").slice(0, mascara.max);
            var novo = mascara.formatar(digitos);
            if (novo === campo.value) return;
            campo.value = novo;
            var pos = 0, vistos = 0;
            while (pos < novo.length && vistos < antesDoCursor) {
                if (/\d/.test(novo[pos])) vistos++;
                pos++;
            }
            campo.setSelectionRange(pos, pos);
        });
    }

    function iniciarCheckout(form) {
        var bloco = form.querySelector("[data-cvv-campo]");
        if (!bloco) return;
        var campo = bloco.querySelector("input");
        var ajuda = bloco.querySelector(".form-help");
        var opcoes = form.querySelectorAll("input[name='forma_pagamento']");

        function atualizar() {
            var marcada = form.querySelector("input[name='forma_pagamento']:checked");
            var cartao = marcada && marcada.dataset.cartao;
            bloco.hidden = !cartao;
            campo.disabled = !cartao;
            if (!cartao) return;
            var amex = marcada.dataset.bandeira === "American Express";
            campo.maxLength = amex ? 4 : 3;
            campo.placeholder = amex ? "••••" : "•••";
            if (ajuda) ajuda.textContent = "Cartão " + marcada.dataset.cartao + ". " +
                (amex ? "4 dígitos na frente do cartão." : "3 dígitos no verso do cartão.") +
                " O código não fica guardado.";
        }

        opcoes.forEach(function (r) { r.addEventListener("change", atualizar); });
        atualizar();
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-mascara]").forEach(aplicarMascara);
        document.querySelectorAll("[data-checkout-pagamento]").forEach(iniciarCheckout);
    });
})();
