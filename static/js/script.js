const campoFotos = document.querySelector("#fotos");
const gradeFotos = document.querySelector("#pre-visualizacao");

let fotosPreparadas = [];
const chavesFotos = new Set();

if (campoFotos && gradeFotos) {
    campoFotos.addEventListener("change", async (evento) => {
        const arquivos = Array.from(evento.target.files || []);

        for (const arquivo of arquivos) {
            if (!arquivo.type.startsWith("image/")) {
                continue;
            }

            const chaveFoto = `${arquivo.name}-${arquivo.size}-${arquivo.lastModified}`;

            if (chavesFotos.has(chaveFoto)) {
                continue;
            }

            try {
                const fotoComprimida = await comprimirImagem(arquivo);
                fotosPreparadas.push(fotoComprimida);
                chavesFotos.add(chaveFoto);
                mostrarFoto(fotoComprimida, chaveFoto);
            } catch (erro) {
                console.error("Não foi possível preparar a foto:", erro);
            }
        }

        campoFotos.value = "";
    });
}

function comprimirImagem(arquivo) {
    return new Promise((resolve, reject) => {
        const imagem = new Image();
        const enderecoTemporario = URL.createObjectURL(arquivo);

        imagem.onload = () => {
            const larguraMaxima = 1600;
            const proporcao = Math.min(1, larguraMaxima / imagem.width);
            const largura = Math.round(imagem.width * proporcao);
            const altura = Math.round(imagem.height * proporcao);

            const canvas = document.createElement("canvas");
            canvas.width = largura;
            canvas.height = altura;

            const contexto = canvas.getContext("2d");

            if (!contexto) {
                URL.revokeObjectURL(enderecoTemporario);
                reject(new Error("Não foi possível obter o contexto do canvas."));
                return;
            }

            contexto.fillStyle = "#ffffff";
            contexto.fillRect(0, 0, largura, altura);
            contexto.drawImage(imagem, 0, 0, largura, altura);

            canvas.toBlob(
                (blob) => {
                    URL.revokeObjectURL(enderecoTemporario);

                    if (!blob) {
                        reject(new Error("Falha ao comprimir a imagem."));
                        return;
                    }

                    const nomeSemExtensao = arquivo.name.replace(/\.[^.]+$/, "");
                    const novoNome = `${nomeSemExtensao}.jpg`;

                    const fotoComprimida = new File([blob], novoNome, {
                        type: "image/jpeg",
                    });

                    resolve(fotoComprimida);
                },
                "image/jpeg",
                0.8
            );
        };

        imagem.onerror = () => {
            URL.revokeObjectURL(enderecoTemporario);
            reject(new Error("O arquivo não pôde ser lido como imagem."));
        };

        imagem.src = enderecoTemporario;
    });
}

function mostrarFoto(arquivo, chaveFoto) {
    const enderecoTemporario = URL.createObjectURL(arquivo);

    const figura = document.createElement("figure");
    figura.className = "foto-selecionada";

    const imagem = document.createElement("img");
    imagem.src = enderecoTemporario;
    imagem.alt = `Pré-visualização de ${arquivo.name}`;

    imagem.onload = () => {
        URL.revokeObjectURL(enderecoTemporario);
    };
        imagem.addEventListener("click", () => {
        const outrasFotos = gradeFotos.querySelectorAll(".foto-selecionada");

        outrasFotos.forEach((outraFoto) => {
            if (outraFoto !== figura) {
                outraFoto.classList.remove("mostrar-acoes");
            }
        });

        figura.classList.toggle("mostrar-acoes");
    });

    const legenda = document.createElement("figcaption");
    legenda.textContent = `${arquivo.name} • ${formatarTamanho(arquivo.size)}`;

    const botaoExcluir = document.createElement("button");
    botaoExcluir.type = "button";
    botaoExcluir.className = "excluir-foto";
    botaoExcluir.textContent = "×";
    botaoExcluir.setAttribute(
        "aria-label",
        `Excluir a foto ${arquivo.name}`
    );

    botaoExcluir.addEventListener("click", (evento) => {
        evento.stopPropagation();
        fotosPreparadas = fotosPreparadas.filter(
            (foto) => foto !== arquivo
        );
        chavesFotos.delete(chaveFoto);
        figura.remove();
    });

    figura.append(imagem, legenda, botaoExcluir);
    gradeFotos.append(figura);
}

function formatarTamanho(bytes) {
    const tamanhoEmKb = Math.max(1, Math.round(bytes / 1024));
    return `${tamanhoEmKb} KB`;
}
const formulario = document.querySelector("#form-semanario");
const botaoSalvar = document.querySelector("#botao-salvar");
const mensagemSalvamento = document.querySelector("#mensagem-salvamento");

const botoesAjuda = document.querySelectorAll(".botao-ajuda");

botoesAjuda.forEach((botao) => {
    botao.addEventListener("click", () => {
        const idAjuda = botao.getAttribute("aria-controls");
        const textoAjuda = document.getElementById(idAjuda);
        const estavaAberto = botao.getAttribute("aria-expanded") === "true";

        botoesAjuda.forEach((outroBotao) => {
            const outroId = outroBotao.getAttribute("aria-controls");
            const outroTexto = document.getElementById(outroId);
            outroBotao.setAttribute("aria-expanded", "false");
            outroTexto.hidden = true;
        });

        if (!estavaAberto) {
            botao.setAttribute("aria-expanded", "true");
            textoAjuda.hidden = false;
        }
    });
});


formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    mensagemSalvamento.textContent = "";
    mensagemSalvamento.className = "";

    botaoSalvar.disabled = true;
    botaoSalvar.textContent = "Salvando...";

    const dados = new FormData(formulario);

    dados.delete("fotos");

    fotosPreparadas.forEach((foto) => {
        dados.append("fotos", foto, foto.name);
    });

    try {
        const resposta = await fetch("/api/semanarios", {
            method: "POST",
            body: dados
        });

        const resultado = await resposta.json();

        if (!resposta.ok) {
            throw new Error(resultado.erro || "Não foi possível salvar.");
        }

        mensagemSalvamento.textContent = resultado.mensagem;
        mensagemSalvamento.className = "mensagem-sucesso";

        formulario.dataset.semanarioId = resultado.id;
    } catch (erro) {
        mensagemSalvamento.textContent = erro.message;
        mensagemSalvamento.className = "mensagem-erro";
    } finally {
        botaoSalvar.disabled = false;
        botaoSalvar.textContent = "Salvar semanário";
    }
});
