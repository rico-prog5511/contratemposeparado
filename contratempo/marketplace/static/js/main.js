/* static/js/main.js — comportamento global (todas as páginas via base.html)
 *
 * Tudo aqui é melhoria progressiva: sem JavaScript, links e formulários
 * continuam funcionando (o Django faz a validação e o processamento).
 *
 * Recursos ativados por atributos no HTML:
 *   .menu-toggle              abre/fecha o menu mobile
 *   .has-dropdown             submenus (categorias, conta)
 *   .messages li              alertas fecháveis (sucesso some sozinho)
 *   form[data-confirm]        pede confirmação antes de enviar
 *   [data-password-toggle]    mostrar/ocultar senha
 *   [data-mask="cep|telefone"] máscara de digitação
 *   [data-cep-lookup]         preenche endereço pelo CEP (ViaCEP)
 *   [data-auto-submit]        envia o form ao mudar um select/checkbox
 *   [data-match="#id"]        confere se dois campos são iguais
 */

document.addEventListener("DOMContentLoaded", function () {

    /* ----- MENU MOBILE ----- */
    var toggle = document.querySelector(".menu-toggle");
    var nav = document.querySelector(".main-nav");

    if (toggle && nav) {
        toggle.addEventListener("click", function () {
            var aberto = nav.classList.toggle("open");
            toggle.setAttribute("aria-expanded", String(aberto));
            toggle.setAttribute("aria-label", aberto ? "Fechar menu" : "Abrir menu");
        });

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && nav.classList.contains("open")) {
                nav.classList.remove("open");
                toggle.setAttribute("aria-expanded", "false");
                toggle.focus();
            }
        });
    }

    /* ----- SUBMENUS (categorias e conta) ----- */
    function fecharSubmenu(item) {
        item.classList.remove("open");
        var botao = item.querySelector(".dropdown-toggle");
        if (botao) botao.setAttribute("aria-expanded", "false");
    }

    document.querySelectorAll(".dropdown-toggle").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            var item = btn.closest(".has-dropdown");
            var estavaAberto = item.classList.contains("open");

            document.querySelectorAll(".has-dropdown.open").forEach(function (aberto) {
                if (aberto !== item) fecharSubmenu(aberto);
            });

            item.classList.toggle("open", !estavaAberto);
            btn.setAttribute("aria-expanded", String(!estavaAberto));
        });
    });

    document.addEventListener("click", function (e) {
        document.querySelectorAll(".has-dropdown.open").forEach(function (item) {
            if (!item.contains(e.target)) fecharSubmenu(item);
        });
    });

    document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;
        document.querySelectorAll(".has-dropdown.open").forEach(fecharSubmenu);
    });

    /* ----- MENSAGENS (django.contrib.messages) ----- */
    function removerMensagem(item) {
        item.classList.add("saindo");
        setTimeout(function () { item.remove(); }, 250);
    }

    document.querySelectorAll(".messages li").forEach(function (item) {
        var fechar = item.querySelector(".message-close");
        if (fechar) {
            fechar.addEventListener("click", function () { removerMensagem(item); });
        }
        // Sucesso some sozinho; erros ficam até o usuário fechar.
        if (item.classList.contains("success")) {
            setTimeout(function () { removerMensagem(item); }, 6000);
        }
    });

    /* ----- CONFIRMAÇÃO ANTES DE ENVIAR (excluir, cancelar, desativar…) ----- */
    var dialogo = document.getElementById("confirm-dialog");

    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            if (form.dataset.confirmado === "1") return;

            // Navegadores sem <dialog>: usa o confirm() nativo.
            if (!dialogo || typeof dialogo.showModal !== "function") {
                if (!window.confirm(form.dataset.confirm)) e.preventDefault();
                return;
            }

            e.preventDefault();
            dialogo.querySelector("#confirm-dialog-title").textContent =
                form.dataset.confirmTitle || "Tem certeza?";
            dialogo.querySelector("#confirm-dialog-text").textContent = form.dataset.confirm;
            dialogo.querySelector("#confirm-dialog-ok").textContent =
                form.dataset.confirmOk || "Confirmar";

            dialogo.returnValue = "";
            dialogo.showModal();
            dialogo.addEventListener("close", function aoFechar() {
                dialogo.removeEventListener("close", aoFechar);
                if (dialogo.returnValue === "ok") {
                    form.dataset.confirmado = "1";
                    if (typeof form.requestSubmit === "function") {
                        form.requestSubmit(e.submitter || undefined);
                    } else {
                        form.submit();
                    }
                }
            });
        });
    });

    /* ----- MOSTRAR / OCULTAR SENHA ----- */
    document.querySelectorAll("[data-password-toggle]").forEach(function (btn) {
        var input = btn.parentElement.querySelector("input");
        if (!input) return;
        btn.addEventListener("click", function () {
            var visivel = input.type === "text";
            input.type = visivel ? "password" : "text";
            btn.textContent = visivel ? "Mostrar" : "Ocultar";
            btn.setAttribute("aria-label", visivel ? "Mostrar senha" : "Ocultar senha");
        });
    });

    /* ----- MÁSCARAS (CEP e telefone) ----- */
    var mascaras = {
        cep: function (v) {
            v = v.replace(/\D/g, "").slice(0, 8);
            return v.length > 5 ? v.slice(0, 5) + "-" + v.slice(5) : v;
        },
        telefone: function (v) {
            v = v.replace(/\D/g, "").slice(0, 11);
            if (v.length <= 2) return v.length ? "(" + v : v;
            if (v.length <= 6) return "(" + v.slice(0, 2) + ") " + v.slice(2);
            if (v.length <= 10) return "(" + v.slice(0, 2) + ") " + v.slice(2, 6) + "-" + v.slice(6);
            return "(" + v.slice(0, 2) + ") " + v.slice(2, 7) + "-" + v.slice(7);
        }
    };

    document.querySelectorAll("[data-mask]").forEach(function (input) {
        var aplicar = mascaras[input.dataset.mask];
        if (!aplicar) return;
        input.addEventListener("input", function () { input.value = aplicar(input.value); });
        if (input.value) input.value = aplicar(input.value);
    });

    /* ---------------------------------------------------------------
       BUSCA DE ENDEREÇO PELO CEP (ViaCEP)
       Os campos a preencher têm data-cep-field="<chave da resposta>".
       --------------------------------------------------------------- */
    document.querySelectorAll("[data-cep-lookup]").forEach(function (input) {
        var form = input.form;
        var status = document.createElement("div");
        status.className = "form-help";
        status.setAttribute("aria-live", "polite");
        input.insertAdjacentElement("afterend", status);

        input.addEventListener("blur", function () {
            var cep = input.value.replace(/\D/g, "");
            if (cep.length !== 8 || !window.fetch) return;

            status.textContent = "Buscando endereço…";
            fetch("https://viacep.com.br/ws/" + cep + "/json/")
                .then(function (r) { return r.json(); })
                .then(function (dados) {
                    if (dados.erro) {
                        status.textContent = "CEP não encontrado. Preencha o endereço manualmente.";
                        return;
                    }
                    form.querySelectorAll("[data-cep-field]").forEach(function (campo) {
                        var valor = dados[campo.dataset.cepField];
                        if (valor && !campo.value) campo.value = valor;
                    });
                    status.textContent = "Endereço preenchido. Confira e informe o número.";
                    var numero = form.querySelector("[name='numero']");
                    if (numero && !numero.value) numero.focus();
                })
                .catch(function () {
                    status.textContent = "";
                });
        });
    });

    /* ---------------------------------------------------------------
       ENVIO AUTOMÁTICO (ordenação, quantidade no carrinho)
       O botão de envio fica em <noscript> no HTML para quem não tem JS.
       --------------------------------------------------------------- */
    document.querySelectorAll("[data-auto-submit]").forEach(function (campo) {
        campo.addEventListener("change", function () {
            if (typeof campo.form.requestSubmit === "function") {
                campo.form.requestSubmit();
            } else {
                campo.form.submit();
            }
        });
    });

    /* ----- CAMPOS QUE PRECISAM SER IGUAIS (confirmar senha) ----- */
    document.querySelectorAll("[data-match]").forEach(function (campo) {
        var original = document.querySelector(campo.dataset.match);
        if (!original) return;
        function conferir() {
            campo.setCustomValidity(
                campo.value && campo.value !== original.value ? "As senhas não coincidem." : ""
            );
        }
        campo.addEventListener("input", conferir);
        original.addEventListener("input", conferir);
    });
});

/* ---------------------------------------------------------------
   SUGESTÕES DA BUSCA (form.search-box[data-sugestoes])
   Busca enquanto digita (mín. 2 letras) e mostra produtos e
   categorias. Setas ↑ ↓ navegam, Enter abre, Esc fecha. Sem JS,
   a busca continua funcionando normalmente pelo formulário.
   --------------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form[data-sugestoes]").forEach(function (form, n) {
        var input = form.querySelector("input[name='q']");
        if (!input || !window.fetch) return;

        var lista = document.createElement("div");
        lista.className = "search-suggest";
        lista.id = "sugestoes-" + n;
        lista.setAttribute("role", "listbox");
        lista.hidden = true;
        form.appendChild(lista);

        input.setAttribute("role", "combobox");
        input.setAttribute("aria-autocomplete", "list");
        input.setAttribute("aria-controls", lista.id);
        input.setAttribute("aria-expanded", "false");

        var timer = null;
        var ultimaBusca = "";
        var indice = -1;

        function opcoes() { return lista.querySelectorAll("[role='option']"); }

        function fechar() {
            lista.hidden = true;
            input.setAttribute("aria-expanded", "false");
            input.removeAttribute("aria-activedescendant");
            indice = -1;
        }

        function destacar(novo) {
            var itens = opcoes();
            if (!itens.length) return;
            indice = (novo + itens.length) % itens.length;
            itens.forEach(function (item, i) { item.classList.toggle("ativa", i === indice); });
            input.setAttribute("aria-activedescendant", itens[indice].id);
            itens[indice].scrollIntoView({ block: "nearest" });
        }

        function elemento(tag, classe, texto) {
            var el = document.createElement(tag);
            if (classe) el.className = classe;
            if (texto) el.textContent = texto;
            return el;
        }

        function mostrar(dados, termo) {
            lista.innerHTML = "";
            var total = 0;

            if (dados.categorias.length) {
                lista.appendChild(elemento("span", "search-suggest-title", "Categorias"));
                dados.categorias.forEach(function (c) {
                    var link = elemento("a", "search-suggest-cat", c.nome);
                    link.href = c.url;
                    link.id = lista.id + "-" + (total++);
                    link.setAttribute("role", "option");
                    lista.appendChild(link);
                });
            }
            if (dados.produtos.length) {
                lista.appendChild(elemento("span", "search-suggest-title", "Produtos"));
                dados.produtos.forEach(function (p) {
                    var link = elemento("a", "search-suggest-item");
                    link.href = p.url;
                    link.id = lista.id + "-" + (total++);
                    link.setAttribute("role", "option");
                    var img = document.createElement("img");
                    img.src = p.imagem;
                    img.alt = "";
                    link.appendChild(img);
                    var info = elemento("span", "search-suggest-info");
                    info.appendChild(elemento("strong", "", p.nome));
                    info.appendChild(elemento("small", "", p.categoria));
                    link.appendChild(info);
                    link.appendChild(elemento("span", "search-suggest-price", p.preco));
                    lista.appendChild(link);
                });
            }

            var todos = elemento("a", "search-suggest-all");
            todos.href = form.action + "?q=" + encodeURIComponent(termo);
            todos.id = lista.id + "-" + (total++);
            todos.setAttribute("role", "option");
            todos.textContent = dados.produtos.length || dados.categorias.length
                ? "Ver todos os resultados para “" + termo + "” →"
                : "Nenhuma sugestão. Buscar “" + termo + "” mesmo assim →";
            lista.appendChild(todos);

            indice = -1;
            lista.hidden = false;
            input.setAttribute("aria-expanded", "true");
        }

        input.addEventListener("input", function () {
            clearTimeout(timer);
            var termo = input.value.trim();
            if (termo.length < 2) { fechar(); ultimaBusca = ""; return; }
            timer = setTimeout(function () {
                if (termo === ultimaBusca) return;
                ultimaBusca = termo;
                fetch(form.dataset.sugestoes + "?q=" + encodeURIComponent(termo), { headers: { "Accept": "application/json" } })
                    .then(function (r) { return r.ok ? r.json() : null; })
                    .then(function (dados) {
                        // Ignora respostas atrasadas de termos antigos
                        if (dados && input.value.trim() === termo) mostrar(dados, termo);
                    })
                    .catch(function () { /* sem sugestões: a busca normal continua funcionando */ });
            }, 220);
        });

        input.addEventListener("keydown", function (e) {
            if (lista.hidden) return;
            if (e.key === "ArrowDown") { e.preventDefault(); destacar(indice + 1); }
            else if (e.key === "ArrowUp") { e.preventDefault(); destacar(indice - 1); }
            else if (e.key === "Escape") { fechar(); }
            else if (e.key === "Enter" && indice >= 0) {
                e.preventDefault();
                window.location.href = opcoes()[indice].href;
            }
        });

        input.addEventListener("focus", function () {
            if (lista.childElementCount && input.value.trim().length >= 2) {
                lista.hidden = false;
                input.setAttribute("aria-expanded", "true");
            }
        });

        document.addEventListener("click", function (e) {
            if (!form.contains(e.target)) fechar();
        });
    });
});

/* ---------------------------------------------------------------
   ERROS DE FORMULÁRIO: ao voltar do envio com erro, o foco vai para
   o primeiro campo inválido (o leitor de tela lê o rótulo e o erro,
   ligados pelo aria-describedby que o Django gera).
   --------------------------------------------------------------- */
document.addEventListener("DOMContentLoaded", function () {
    var invalido = document.querySelector("main [aria-invalid='true']");
    if (!invalido) return;
    invalido.focus({ preventScroll: true });
    invalido.scrollIntoView({ block: "center", behavior: "auto" });
});
