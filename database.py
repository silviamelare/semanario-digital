import sqlite3
from contextlib import nullcontext
from pathlib import Path
from werkzeug.security import check_password_hash, generate_password_hash


PASTA_PROJETO = Path(__file__).resolve().parent
CAMINHO_BANCO = PASTA_PROJETO / "semanario.db"


def conectar():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_banco():
    with conectar() as conexao:
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS semanarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professora TEXT NOT NULL,
                turma TEXT NOT NULL,
                periodo TEXT NOT NULL,
                ciclo TEXT NOT NULL,
                inicio_semana TEXT NOT NULL,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS registros_diarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semanario_id INTEGER NOT NULL,
                dia_numero INTEGER NOT NULL CHECK (dia_numero BETWEEN 1 AND 5),
                proposta TEXT,
                intencionalidade TEXT,
                desenvolvimento TEXT,
                observacao TEXT,
                registro_reflexivo TEXT,
                FOREIGN KEY (semanario_id)
                    REFERENCES semanarios(id)
                    ON DELETE CASCADE,
                UNIQUE (semanario_id, dia_numero)
            );

            CREATE TABLE IF NOT EXISTS fotos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semanario_id INTEGER NOT NULL,
                nome_arquivo TEXT NOT NULL,
                caminho TEXT NOT NULL,
                FOREIGN KEY (semanario_id)
                    REFERENCES semanarios(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                rf TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                perfil TEXT NOT NULL
                    CHECK (perfil IN ('professora', 'ap_diretora', 'administrativo')),
                primeiro_acesso INTEGER NOT NULL DEFAULT 1
                    CHECK (primeiro_acesso IN (0, 1)),
                ativo INTEGER NOT NULL DEFAULT 1
                    CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vinculos_anuais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                ano INTEGER NOT NULL,
                turma TEXT NOT NULL,
                periodo TEXT NOT NULL,
                ciclo TEXT NOT NULL,
                FOREIGN KEY (usuario_id)
                    REFERENCES usuarios(id)
                    ON DELETE CASCADE,
                UNIQUE (usuario_id, ano, turma, periodo)
            );
            """
        )


PERFIS_VALIDOS = {"professora", "ap_diretora", "administrativo"}


def cadastrar_usuario(nome, rf, senha_provisoria, perfil, conexao=None):
    nome = nome.strip()
    rf = rf.strip()
    perfil = perfil.strip().lower()

    if not nome:
        raise ValueError("O nome é obrigatório.")

    if not rf:
        raise ValueError("O RF é obrigatório.")

    if not senha_provisoria:
        raise ValueError("A senha provisória é obrigatória.")

    if perfil not in PERFIS_VALIDOS:
        raise ValueError("Perfil de usuário inválido.")

    senha_hash = generate_password_hash(senha_provisoria)

    gerenciador = nullcontext(conexao) if conexao is not None else conectar()
    with gerenciador as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO usuarios (
                nome,
                rf,
                senha_hash,
                perfil
            )
            VALUES (?, ?, ?, ?)
            """,
            (nome, rf, senha_hash, perfil),
        )

    return cursor.lastrowid


def buscar_usuario_por_rf(rf):
    with conectar() as conexao:
        return conexao.execute(
            """
            SELECT *
            FROM usuarios
            WHERE rf = ?
            """,
            (rf.strip(),),
        ).fetchone()


def autenticar_usuario(rf, senha):
    usuario = buscar_usuario_por_rf(rf)

    if usuario is None:
        return None

    if not usuario["ativo"]:
        return None

    if not check_password_hash(usuario["senha_hash"], senha):
        return None

    return usuario


def alterar_senha(usuario_id, nova_senha):
    if len(nova_senha) < 8:
        raise ValueError("A nova senha deve ter pelo menos 8 caracteres.")

    nova_senha_hash = generate_password_hash(nova_senha)

    with conectar() as conexao:
        cursor = conexao.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?,
                primeiro_acesso = 0
            WHERE id = ?
              AND ativo = 1
            """,
            (nova_senha_hash, usuario_id),
        )

        return cursor.rowcount == 1



def cadastrar_vinculo(usuario_id, ano, turma, periodo, ciclo, conexao=None):
    ano = int(ano)
    turma = turma.strip()
    periodo = periodo.strip()
    ciclo = ciclo.strip()

    if ano < 2000 or ano > 2100:
        raise ValueError("Ano letivo inválido.")

    if not turma:
        raise ValueError("A turma é obrigatória.")

    if not periodo:
        raise ValueError("O período é obrigatório.")

    if not ciclo:
        raise ValueError("O ciclo é obrigatório.")

    gerenciador = nullcontext(conexao) if conexao is not None else conectar()
    with gerenciador as conexao:
        usuario = conexao.execute(
            """
            SELECT perfil, ativo
            FROM usuarios
            WHERE id = ?
            """,
            (usuario_id,),
        ).fetchone()

        if usuario is None or not usuario["ativo"]:
            raise ValueError("Usuário não encontrado ou inativo.")

        if usuario["perfil"] != "professora":
            raise ValueError("Somente professoras recebem vínculo com turma.")

        cursor = conexao.execute(
            """
            INSERT INTO vinculos_anuais (
                usuario_id,
                ano,
                turma,
                periodo,
                ciclo
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (usuario_id, ano, turma, periodo, ciclo),
        )

        return cursor.lastrowid