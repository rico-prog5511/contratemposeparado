/* static/js/upload.js — pré-visualização de imagens antes do envio
 *
 *   [data-avatar-preview]      troca a foto de perfil ao escolher um arquivo
 *   [data-upload-preview]      lista miniaturas das imagens novas do anúncio
 *                              (o input fica dentro de [data-upload-area])
 *   [data-remove-image]        checkbox "remover" marca a miniatura existente
 */

document.addEventListener("DOMContentLoaded", function () {

    function lerImagem(arquivo, callback) {
        if (!arquivo || arquivo.type.indexOf("image/") !== 0) return;
        var leitor = new FileReader();
        leitor.onload = function (e) { callback(e.target.result); };
        leitor.readAsDataURL(arquivo);
    }

    /* Foto de perfil */
    var avatar = document.querySelector("[data-avatar-preview]");
    if (avatar) {
        var inputAvatar = document.querySelector("input[type='file'][name='avatar_arquivo']");
        if (inputAvatar) {
            inputAvatar.addEventListener("change", function () {
                lerImagem(inputAvatar.files[0], function (src) {
                    avatar.innerHTML = "";
                    var img = document.createElement("img");
                    img.src = src;
                    img.alt = "Nova foto de perfil";
                    avatar.appendChild(img);
                });
            });
        }
    }

    /* Imagens do anúncio */
    var area = document.querySelector("[data-upload-area]");
    var lista = document.querySelector("[data-upload-preview]");
    if (area && lista) {
        var inputImagens = area.querySelector("input[type='file']");
        var limite = parseInt(area.dataset.limite || "8", 10);
        var aviso = area.querySelector("[data-upload-aviso]");

        function existentesMantidas() {
            return document.querySelectorAll("[data-remove-image]:not(:checked)").length;
        }

        inputImagens.addEventListener("change", function () {
            lista.innerHTML = "";
            var arquivos = Array.prototype.slice.call(inputImagens.files);
            var disponiveis = limite - existentesMantidas();

            if (aviso) {
                aviso.textContent = arquivos.length > disponiveis
                    ? "Você selecionou " + arquivos.length + " imagens, mas só cabem mais " + Math.max(disponiveis, 0) + "."
                    : "";
            }

            arquivos.forEach(function (arquivo, i) {
                lerImagem(arquivo, function (src) {
                    var item = document.createElement("li");
                    item.className = "upload-thumb" + (i >= disponiveis ? " upload-thumb--excede" : "");
                    var img = document.createElement("img");
                    img.src = src;
                    img.alt = arquivo.name;
                    item.appendChild(img);
                    lista.appendChild(item);
                });
            });
        });

        // Arrastar e soltar sobre a área
        ["dragenter", "dragover"].forEach(function (ev) {
            area.addEventListener(ev, function (e) { e.preventDefault(); area.classList.add("dragging"); });
        });
        ["dragleave", "drop"].forEach(function (ev) {
            area.addEventListener(ev, function () { area.classList.remove("dragging"); });
        });
        area.addEventListener("drop", function (e) {
            e.preventDefault();
            if (e.dataTransfer && e.dataTransfer.files.length) {
                inputImagens.files = e.dataTransfer.files;
                inputImagens.dispatchEvent(new Event("change"));
            }
        });
    }

    /* Imagens existentes marcadas para remoção */
    document.querySelectorAll("[data-remove-image]").forEach(function (checkbox) {
        var card = checkbox.closest(".image-manage-item");
        checkbox.addEventListener("change", function () {
            if (card) card.classList.toggle("removendo", checkbox.checked);
        });
    });
});
