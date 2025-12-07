from flask import Flask, jsonify
from flask_cors import CORS

from routes.Login.auth import auth_bp
from routes.Login.register import register_bp
from routes.Ip.register_ip import ip_bp
from routes.Ip.litar_ip import listar_ip_bp
from routes.vlms.calcular_vlms import calcular_vlms_bp

app = Flask(__name__)

CORS(app,
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Content-Type"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

app.register_blueprint(auth_bp)
app.register_blueprint(register_bp)
app.register_blueprint(ip_bp)
app.register_blueprint(listar_ip_bp)
app.register_blueprint(calcular_vlms_bp)

@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    return response

@app.route("/")
def index():
    return jsonify({"Acceso denegado": "Comunicate con el administrador para obtener acceso."})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
