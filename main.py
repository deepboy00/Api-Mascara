from flask import Flask, jsonify
from routes.Login.auth import auth_bp
from routes.Login.register import register_bp

app = Flask(__name__)

app.register_blueprint(auth_bp)
app.register_blueprint(register_bp)

@app.route('/')
def index():
    return jsonify({"Acceso denegado": "Comunicate con el administrador para obtener acceso."})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
