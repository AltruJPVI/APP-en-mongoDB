from app import create_app #__init__.py toma el nombre de la carpeta que lo contiene.

app = create_app()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )


'''
python run.py
    ↓
create_app() crea instancia: app = Flask(__name__)
    ↓
Se configuran rutas con @app.route(...)
    ↓
app.run() arranca el servidor
    ↓
Servidor escuchando en puerto 5000
    ↓
Usuario visita http://localhost:5000/health
    ↓
Flask ejecuta health()
    ↓
Devuelve respuesta JSON
'''