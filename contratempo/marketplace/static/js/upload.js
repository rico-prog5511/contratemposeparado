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

    /* Imagens do anúncio
     *
     * O campo de arquivo do navegador TROCA a seleção a cada escolha. Para
     * dar para adicionar fotos aos poucos (uma por vez, várias juntas ou
     * arrastando), as fotos escolhidas ficam numa lista aqui e o campo é
     * remontado com todas elas (DataTransfer) a cada mudança. Cada miniatura
     * tem um botão para tirar a foto antes de enviar.
     */
    var area = document.querySelector("[data-upload-area]");
    var lista = document.querySelector("[data-upload-preview]");
    if (area && lista) {
        var inputImagens = area.querySelector("input[type='file']");
        var limite = parseInt(area.dataset.limite || "8", 10);
        var tamanhoMax = parseInt(area.dataset.tamanhoMax || "0", 10);
        var aviso = area.querySelector("[data-upload-aviso]");
        var selecionadas = [];
        var enderecos = [];

        var acumula = (function () {
            try { return !!new DataTransfer().items; } catch (e) { return false; }
        })();

        function existentesMantidas() {
            return document.querySelectorAll("[data-remove-image]:not(:checked)").length;
        }

        function disponiveis() {
            return Math.max(limite - existentesMantidas(), 0);
        }

        function plural(n, um, varios) { return n + " " + (n === 1 ? um : varios); }

        function avisar(texto) {
            if (aviso) aviso.textContent = texto;
        }

        function resumo() {
            var total = existentesMantidas() + selecionadas.length;
            return plural(total, "foto", "fotos") + " de " + limite + ".";
        }

        function sincronizar() {
            var dados = new DataTransfer();
            selecionadas.forEach(function (arquivo) { dados.items.add(arquivo); });
            inputImagens.files = dados.files;
        }

        function desenhar() {
            enderecos.forEach(function (url) { URL.revokeObjectURL(url); });
            enderecos = [];
            lista.innerHTML = "";
            var cabem = disponiveis();
            selecionadas.forEach(function (arquivo, i) {
                var item = document.createElement("li");
                item.className = "upload-thumb" + (i >= cabem ? " upload-thumb--excede" : "");
                var img = document.createElement("img");
                var url = URL.createObjectURL(arquivo);
                enderecos.push(url);
                img.src = url;
                img.alt = "Nova foto: " + arquivo.name;
                item.appendChild(img);

                var remover = document.createElement("button");
                remover.type = "button";
                remover.className = "upload-thumb-remover";
                remover.setAttribute("aria-label", "Tirar a foto " + arquivo.name);
                remover.textContent = "×";
                remover.addEventListener("click", function () {
                    selecionadas.splice(i, 1);
                    sincronizar();
                    desenhar();
                    avisar("Foto retirada. " + resumo());
                    var botoes = lista.querySelectorAll(".upload-thumb-remover");
                    (botoes[Math.min(i, botoes.length - 1)] || inputImagens).focus();
                });
                item.appendChild(remover);
                lista.appendChild(item);
            });
        }

        function adicionar(arquivos) {
            var novas = 0, repetidas = 0, grandes = 0, sobrando = 0, invalidas = 0;
            Array.prototype.forEach.call(arquivos, function (arquivo) {
                if (arquivo.type.indexOf("image/") !== 0) { invalidas++; return; }
                if (tamanhoMax && arquivo.size > tamanhoMax) { grandes++; return; }
                var igual = selecionadas.some(function (f) {
                    return f.name === arquivo.name && f.size === arquivo.size && f.lastModified === arquivo.lastModified;
                });
                if (igual) { repetidas++; return; }
                if (selecionadas.length >= disponiveis()) { sobrando++; return; }
                selecionadas.push(arquivo);
                novas++;
            });
            sincronizar();
            desenhar();

            var partes = [];
            if (novas) partes.push(plural(novas, "foto adicionada", "fotos adicionadas") + ".");
            if (sobrando) partes.push(plural(sobrando, "foto ficou", "fotos ficaram") + " de fora: o limite é " + limite + " por anúncio.");
            if (grandes) partes.push(plural(grandes, "foto passou", "fotos passaram") + " de 5 MB e não " + (grandes === 1 ? "foi adicionada" : "foram adicionadas") + ".");
            if (invalidas) partes.push(plural(invalidas, "arquivo não é imagem", "arquivos não são imagens") + ".");
            if (repetidas) partes.push(plural(repetidas, "foto já estava", "fotos já estavam") + " na lista.");
            avisar(partes.join(" ") + " " + resumo());
        }

        inputImagens.addEventListener("change", function () {
            if (!acumula) {
                // Navegador antigo: sem como somar seleções; mostra só a escolha atual.
                selecionadas = Array.prototype.slice.call(inputImagens.files);
                desenhar();
                lista.querySelectorAll(".upload-thumb-remover").forEach(function (b) { b.remove(); });
                avisar("Dica: segure Ctrl (ou Cmd) para escolher várias fotos de uma vez. " + resumo());
                return;
            }
            // Aqui inputImagens.files tem só a escolha NOVA: soma à lista.
            adicionar(inputImagens.files);
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
            if (!(e.dataTransfer && e.dataTransfer.files.length)) return;
            if (acumula) {
                adicionar(e.dataTransfer.files);
            } else {
                inputImagens.files = e.dataTransfer.files;
                inputImagens.dispatchEvent(new Event("change"));
            }
        });

        // Marcar/desmarcar "remover" numa foto já salva muda quantas novas cabem.
        document.querySelectorAll("[data-remove-image]").forEach(function (checkbox) {
            checkbox.addEventListener("change", function () {
                desenhar();
                avisar(resumo());
            });
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
