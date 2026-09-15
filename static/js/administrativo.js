const campoPerfil = document.getElementById("perfil");
const dadosVinculo = document.getElementById("dados-vinculo");

if (campoPerfil && dadosVinculo) {
    const camposVinculo = dadosVinculo.querySelectorAll(
        "input, select"
    );

    function atualizarCamposVinculo() {
        const professora = campoPerfil.value === "professora";

        dadosVinculo.hidden = !professora;

        camposVinculo.forEach((campo) => {
            campo.required = professora;
        });
    }

    campoPerfil.addEventListener(
        "change",
        atualizarCamposVinculo
    );

    atualizarCamposVinculo();
}
const botaoCopiarSenha = document.getElementById(
    "copiar-senha"
);
const campoSenhaProvisoria = document.getElementById(
    "senha-provisoria"
);

if (botaoCopiarSenha && campoSenhaProvisoria) {
    botaoCopiarSenha.addEventListener(
        "click",
        async () => {
            await navigator.clipboard.writeText(
                campoSenhaProvisoria.value
            );

            botaoCopiarSenha.textContent = "Senha copiada!";

            setTimeout(() => {
                botaoCopiarSenha.textContent = "Copiar senha";
            }, 2000);
        }
    );
}
const formularioAdministrativo = document.querySelector(
    ".form-administrativo"
);

if (formularioAdministrativo && campoSenhaProvisoria) {
    formularioAdministrativo
        .querySelectorAll("input, select")
        .forEach((campo) => {
            if (campo.tagName === "SELECT") {
                campo.selectedIndex = 0;
            } else {
                campo.value = "";
            }
        });

    campoPerfil.dispatchEvent(new Event("change"));
}
