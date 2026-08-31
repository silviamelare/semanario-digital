import sqlite3
from pathlib import Path


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
            """
        )
