from flask import Flask, jsonify, request, make_response
from flask_cors import CORS, cross_origin
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy
import jwt
import datetime
from functools import wraps

# configuro app y db
app = Flask(__name__)
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "mysql+pymysql://grupo41:123456@localhost:3306/apiespacios"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "super-secret"

# Configuracion de CORS para swagger
cors = CORS(app)


db = SQLAlchemy(app)
ma = Marshmallow(app)

# ESPACIO
class Espacio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    reserved = db.Column(db.Boolean)

    def __init__(self, name, start_date, end_date):
        self.name = name
        self.start_date = start_date
        self.end_date = end_date

    def editar(self, reserved):
        """Edita un espacio"""
        self.reserved = reserved
        db.session.commit()


class EspacioSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "start_date", "end_date")


# PEDIDO
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    colection_id = db.Column(db.Integer)
    espacio_id = db.Column(db.Integer, db.ForeignKey("espacio.id"))

    def __init__(self, user_id, colection_id, espacio_id):
        self.user_id = user_id
        self.colection_id = colection_id
        self.espacio_id = espacio_id


class PedidoSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_id", "colection_id", "espacio_id")


# USER
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    password = db.Column(db.String(50))

    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


# creo las tablas
with app.app_context():
    db.create_all()


def token_required(f):
    @wraps(f)
    def decorated():
        token = request.headers["Authorization"].split(" ")[1]
        print(token)
        if not token:
            return jsonify({"message": "El token no existe"}), 401
        try:
            jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except:
            return jsonify({"message": "El token ha expirado o es inválido"}), 401
        return f()

    return decorated


# defino las rutas
@cross_origin
@app.route("/login", methods=["PUT"])
def login():
    username = request.json["username"]
    password = request.json["password"]
    user = User.query.filter_by(username=username).first()
    if user and user.password == password:
        token = jwt.encode(
            {
                "user": username,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=40),
            },
            app.config["SECRET_KEY"],
        )
        return jsonify({"token": token})
    return make_response("Usuario o contraseña incorrectos", 401)


@cross_origin
@app.route("/espacios", methods=["PUT"])
@token_required
def get_spaces():
    start_date = datetime.datetime.now().strftime("%Y-%m-%d")
    end_date = datetime.datetime.strptime(request.json["end_date"], "%Y-%m-%d").date()
    # busco los espacios que contengan la fecha requerida
    spaces = Espacio.query.filter(
        Espacio.end_date <= end_date, Espacio.start_date > start_date, Espacio.reserved == 0
    ).all()
    return jsonify(EspacioSchema(many=True).dump(spaces))


@cross_origin
@app.route("/reservar_espacio", methods=["PUT"])
@token_required
def reserve_space():
    space_id = request.json["space_id"]
    user_id = request.json["user_id"]
    colection_id = request.json["colection_id"]
    space = Espacio.query.get(space_id)
    space.editar(1)
    pedido = Pedido(user_id, colection_id, space_id)
    db.session.add(pedido)
    db.session.commit()
    return jsonify(PedidoSchema(many=False).dump(pedido))


# corro la app con debug true para que se actualice dinamicamente
if __name__ == ("__main__"):
    app.run(debug=True)
