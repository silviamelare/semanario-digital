
const controlesMostrarSenha = document.querySelectorAll(
	"[data-mostrar-senha]"
);

controlesMostrarSenha.forEach((controle) => {
	controle.addEventListener("change", () => {
		const campos = controle.dataset.mostrarSenha.split(",");

		campos.forEach((idCampo) => {
			const campo = document.getElementById(idCampo.trim());

			if (campo) {
				campo.type = controle.checked
					? "text"
					: "password";
			}
		});
	});
});
