from io import BytesIO
import re

import pytest

import app as modulo_app
import database


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    caminho_banco_teste = tmp_path / "semanario_teste.db"
    pasta_uploads_teste = tmp_path / "uploads"
    pasta_uploads_teste.mkdir()

    monkeypatch.setattr(database, "CAMINHO_BANCO", caminho_banco_teste)
    monkeypatch.setattr(modulo_app, "PASTA_UPLOADS", pasta_uploads_teste)
    monkeypatch.setitem(modulo_app.app.config, "TESTING", True)

    database.criar_banco()

    with modulo_app.app.test_client() as cliente_teste:
        with cliente_teste.session_transaction() as sessao:
            sessao["usuario_id"] = 1
            sessao["usuario_nome"] = "Professora Teste"
            sessao["usuario_perfil"] = "professora"

    yield cliente_teste

def test_professora_nao_acessa_cadastro(cliente):
    resposta = cliente.get("/administrativo/usuarios/novo")

    assert resposta.status_code == 403

def test_administrativo_acessa_cadastro(cliente):
    with cliente.session_transaction() as sessao:
        sessao["usuario_perfil"] = "administrativo"

    resposta = cliente.get("/administrativo/usuarios/novo")

    assert resposta.status_code == 200

def test_senha_exibida_autentica_professora(cliente):
    with cliente.session_transaction() as sessao:
        sessao["usuario_perfil"] = "administrativo"

    resposta = cliente.post(
        "/administrativo/usuarios/novo",
        data={
            "nome": "Professora Automática",
            "rf": "RF_AUTOMATICO_001",
            "perfil": "professora",
            "ano": "2026",
            "turma": "Borboleta",
            "periodo": "manha",
            "ciclo": "bercario",
        },
    )

    assert resposta.status_code == 200

    html = resposta.get_data(as_text=True)
    senha_na_tela = re.search(
        r'id="senha-provisoria"\s+value="([^"]+)"',
        html,
    )

    assert senha_na_tela is not None
    usuario = database.autenticar_usuario(
        "RF_AUTOMATICO_001",
        senha_na_tela.group(1),
    )
    assert usuario is not None

    with database.conectar() as conexao:
        vinculo = conexao.execute(
            """
            SELECT ano, turma, periodo, ciclo
            FROM vinculos_anuais
            WHERE usuario_id = ?
            """,
            (usuario["id"],),
        ).fetchone()

    assert vinculo is not None
    assert vinculo["ano"] == 2026
    assert vinculo["turma"] == "Borboleta"

    assert vinculo["periodo"] == "manha"
    assert vinculo["ciclo"] == "bercario"

def dados_validos():
    dados = {
        "professora": "Professora Teste",
        "turma": "Girassol",
        "periodo": "manha",
        "ciclo": "bercario",
        "inicio_semana": "2026-08-31",
    }

    for dia_numero in range(1, 6):
        dados[f"proposta_{dia_numero}"] = f"Proposta {dia_numero}"
        dados[f"intencionalidade_{dia_numero}"] = (
            f"Intencionalidade {dia_numero}"
        )
        dados[f"desenvolvimento_{dia_numero}"] = (
            f"Desenvolvimento {dia_numero}"
        )
        dados[f"observacao_{dia_numero}"] = f"Observação {dia_numero}"
        dados[f"registro_{dia_numero}"] = f"Registro {dia_numero}"

    return dados


def test_pagina_inicial_abre(cliente):
    resposta = cliente.get("/")

    assert resposta.status_code == 200
    assert "Planejamento semanal" in resposta.get_data(as_text=True)


def test_lista_vazia_abre(cliente):
    resposta = cliente.get("/semanarios")

    assert resposta.status_code == 200
    assert "Nenhum semanário foi salvo ainda" in resposta.get_data(
        as_text=True
    )


def test_salvar_exige_identificacao_completa(cliente):
    resposta = cliente.post(
        "/api/semanarios",
        data={"professora": "Professora Teste"},
    )

    assert resposta.status_code == 400
    assert resposta.get_json() == {
        "erro": "Preencha todos os dados de identificação."
    }


def test_salva_semanario_com_dias_e_multiplas_fotos(cliente):
    dados = dados_validos()
    dados["fotos"] = [
        (BytesIO(b"conteudo-foto-1"), "foto-1.jpg"),
        (BytesIO(b"conteudo-foto-2"), "foto-2.png"),
    ]

    resposta = cliente.post(
        "/api/semanarios",
        data=dados,
        content_type="multipart/form-data",
    )

    assert resposta.status_code == 201
    resultado = resposta.get_json()
    assert resultado["mensagem"] == "Semanário salvo com sucesso!"
    assert resultado["id"] == 1

    with database.conectar() as conexao:
        total_semanarios = conexao.execute(
            "SELECT COUNT(*) FROM semanarios"
        ).fetchone()[0]
        total_registros = conexao.execute(
            "SELECT COUNT(*) FROM registros_diarios WHERE semanario_id = 1"
        ).fetchone()[0]
        fotos = conexao.execute(
            "SELECT nome_arquivo, caminho FROM fotos WHERE semanario_id = 1 "
            "ORDER BY id"
        ).fetchall()

    assert total_semanarios == 1
    assert total_registros == 5
    assert [foto["nome_arquivo"] for foto in fotos] == [
        "foto-1.jpg",
        "foto-2.png",
    ]

    for foto in fotos:
        assert (modulo_app.PASTA_UPLOADS / foto["caminho"]).exists()


def test_semanario_salvo_aparece_na_lista_e_abre(cliente):
    resposta_salvar = cliente.post(
        "/api/semanarios",
        data=dados_validos(),
    )
    semanario_id = resposta_salvar.get_json()["id"]

    resposta_lista = cliente.get("/semanarios")
    texto_lista = resposta_lista.get_data(as_text=True)

    assert resposta_lista.status_code == 200
    assert "Professora Teste" in texto_lista
    assert "Girassol" in texto_lista
    assert "31/08/2026" in texto_lista

    resposta_detalhe = cliente.get(f"/semanarios/{semanario_id}")
    texto_detalhe = resposta_detalhe.get_data(as_text=True)

    assert resposta_detalhe.status_code == 200
    assert "Proposta 1" in texto_detalhe
    assert "Registro 5" in texto_detalhe


def test_semanario_inexistente_retorna_404(cliente):
    resposta = cliente.get("/semanarios/999")

    assert resposta.status_code == 404


def test_upload_salvo_pode_ser_acessado(cliente):
    dados = dados_validos()
    dados["fotos"] = [(BytesIO(b"imagem-de-teste"), "foto.jpg")]
    cliente.post(
        "/api/semanarios",
        data=dados,
        content_type="multipart/form-data",
    )

    with database.conectar() as conexao:
        caminho = conexao.execute(
            "SELECT caminho FROM fotos WHERE semanario_id = 1"
        ).fetchone()["caminho"]

    resposta = cliente.get(f"/uploads/{caminho}")

    assert resposta.status_code == 200
    assert resposta.data == b"imagem-de-teste"

def test_pagina_inicial_exige_login(cliente):
    with cliente.session_transaction() as sessao:
        sessao.clear()

    resposta = cliente.get("/")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/login")


def test_api_exige_login(cliente):
    with cliente.session_transaction() as sessao:
        sessao.clear()

    resposta = cliente.post(
        "/api/semanarios",
        data=dados_validos(),
    )

    assert resposta.status_code == 401
    assert resposta.get_json() == {
        "erro": "Faça login para continuar."
    }