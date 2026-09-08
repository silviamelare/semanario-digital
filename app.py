from functools import wraps
from os import environ
from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,

)

from database import (
    alterar_senha,
    autenticar_usuario,
    conectar,
    criar_banco,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = environ.get(
    "SECRET_KEY",
    "chave-utilizada-somente-no-desenvolvimento",
)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

PASTA_UPLOADS = Path(__file__).resolve().parent / "uploads"
PASTA_UPLOADS.mkdir(exist_ok=True)

criar_banco()
def login_obrigatorio(funcao):
    @wraps(funcao)
    def funcao_protegida(*args, **kwargs):
        if "usuario_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify(
                    {"erro": "Faça login para continuar."}
                ), 401

            return redirect(url_for("login"))

        return funcao(*args, **kwargs)

    return funcao_protegida

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None

    if request.method == "POST":
        rf = request.form.get("rf", "")
        senha = request.form.get("senha", "")
        usuario = autenticar_usuario(rf, senha)

        if usuario is None:
            erro = "RF ou senha inválidos."
        else:
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            session["usuario_perfil"] = usuario["perfil"]

            if usuario["primeiro_acesso"]:
                return redirect(url_for("trocar_senha"))

            return redirect(url_for("inicio"))

    return render_template("login.html", erro=erro)


@app.route("/trocar-senha", methods=["GET", "POST"])
def trocar_senha():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    erro = None

    if request.method == "POST":
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if nova_senha != confirmar_senha:
            erro = "As senhas digitadas não são iguais."
        else:
            try:
                senha_alterada = alterar_senha(
                    session["usuario_id"],
                    nova_senha,
                )
            except ValueError as excecao:
                erro = str(excecao)
            else:
                if not senha_alterada:
                    session.clear()
                    return redirect(url_for("login"))

                return redirect(url_for("inicio"))

    return render_template(
        "trocar_senha.html",
        erro=erro,
    )
@app.post("/logout")
@login_obrigatorio
def logout():
    session.clear()
    return redirect(url_for("login"))
@app.route("/")
@login_obrigatorio
def inicio():
    dias_semana = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira"
    ]
    return render_template("index.html", dias=dias_semana)
@app.get("/semanarios")
@login_obrigatorio
def listar_semanarios():
    with conectar() as conexao:
        semanarios = conexao.execute(
            """
            SELECT
                id,
                professora,
                turma,
                periodo,
                ciclo,
                inicio_semana
            FROM semanarios
            ORDER BY inicio_semana DESC, id DESC
            """
        ).fetchall()

    return render_template(
        "lista.html",
        semanarios=semanarios
    )


@app.get("/semanarios/<int:semanario_id>")
@login_obrigatorio
def visualizar_semanario(semanario_id):
    with conectar() as conexao:
        semanario = conexao.execute(
            """
            SELECT *
            FROM semanarios
            WHERE id = ?
            """,
            (semanario_id,)
        ).fetchone()

        if semanario is None:
            abort(404)

        registros = conexao.execute(
            """
            SELECT *
            FROM registros_diarios
            WHERE semanario_id = ?
            ORDER BY dia_numero
            """,
            (semanario_id,)
        ).fetchall()

        fotos = conexao.execute(
            """
            SELECT *
            FROM fotos
            WHERE semanario_id = ?
            ORDER BY id
            """,
            (semanario_id,)
        ).fetchall()

    dias_semana = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira"
    ]

    return render_template(
        "detalhe.html",
        semanario=semanario,
        registros=registros,
        fotos=fotos,
        dias=dias_semana
    )


@app.get("/uploads/<path:nome_arquivo>")
@login_obrigatorio
def mostrar_upload(nome_arquivo):
    return send_from_directory(PASTA_UPLOADS, nome_arquivo)

@app.post("/api/semanarios")
@login_obrigatorio
def salvar_semanario():
    dados_identificacao = {
        "professora": request.form.get("professora", "").strip(),
        "turma": request.form.get("turma", "").strip(),
        "periodo": request.form.get("periodo", "").strip(),
        "ciclo": request.form.get("ciclo", "").strip(),
        "inicio_semana": request.form.get("inicio_semana", "").strip()
    }

    campos_vazios = [
        campo
        for campo, valor in dados_identificacao.items()
        if not valor
    ]

    if campos_vazios:
        return jsonify(
            {"erro": "Preencha todos os dados de identificação."}
        ), 400

    with conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO semanarios (
                professora,
                turma,
                periodo,
                ciclo,
                inicio_semana
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            tuple(dados_identificacao.values())
        )

        semanario_id = cursor.lastrowid

        for dia_numero in range(1, 6):
            conexao.execute(
                """
                INSERT INTO registros_diarios (
                    semanario_id,
                    dia_numero,
                    proposta,
                    intencionalidade,
                    desenvolvimento,
                    observacao,
                    registro_reflexivo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    semanario_id,
                    dia_numero,
                    request.form.get(f"proposta_{dia_numero}", ""),
                    request.form.get(f"intencionalidade_{dia_numero}", ""),
                    request.form.get(f"desenvolvimento_{dia_numero}", ""),
                    request.form.get(f"observacao_{dia_numero}", ""),
                    request.form.get(f"registro_{dia_numero}", "")
                )
            )

        for foto in request.files.getlist("fotos"):
            if not foto or not foto.mimetype.startswith("image/"):
                continue

            nome_salvo = f"{uuid4().hex}.jpg"
            caminho_foto = PASTA_UPLOADS / nome_salvo
            foto.save(caminho_foto)

            conexao.execute(
                """
                INSERT INTO fotos (
                    semanario_id,
                    nome_arquivo,
                    caminho
                )
                VALUES (?, ?, ?)
                """,
                (semanario_id, foto.filename, nome_salvo)
            )

    return jsonify(
        {
            "mensagem": "Semanário salvo com sucesso!",
            "id": semanario_id
        }
    ), 201
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
