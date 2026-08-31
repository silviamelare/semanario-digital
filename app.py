from flask import Flask, render_template

app = Flask(__name__)


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
