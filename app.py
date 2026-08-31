from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_from_directory
)

from database import conectar, criar_banco

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

PASTA_UPLOADS = Path(__file__).resolve().parent / "uploads"
PASTA_UPLOADS.mkdir(exist_ok=True)

criar_banco()

@app.route("/")
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
def mostrar_upload(nome_arquivo):
    return send_from_directory(PASTA_UPLOADS, nome_arquivo)

@app.post("/api/semanarios")
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
