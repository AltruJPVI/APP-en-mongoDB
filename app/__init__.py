from flask import Flask
from app.extensiones import init_db
from app.routes.auth import bp as bp_auth
from app.routes.usuarios import bp as bp_users
from app.routes.comentarios import bp as bp_com
from app.routes.post import bp as bp_post
from app.routes.productos import bp as bp_prod
from app.routes.pedidos import bp as bp_ped




def create_app():
    app,mongo_client = Flask(__name__) #__name__ dentro de __init__.py toma el nombre de la carpeta que lo contiene (app).
    db=init_db()#creamos la instancia de mongoDB
    
    #conexiones
    app.register_blueprint(bp_auth)
    app.register_blueprint(bp_users)
    app.register_blueprint(bp_com)
    app.register_blueprint(bp_ped)
    app.register_blueprint(bp_prod)
    app.register_blueprint(bp_post)

    app.db=db#le pasamos como variable la base de datos a la app
    app.mongo_client=mongo_client
    @app.route('/')
    def index():
        return {"message": "API Tienda de Tenis"}
    
    @app.route('/health')
    def health():
        try:
            db.command('ping')#intenta conectar con la db
            return {"status": "connected"}
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
    
    return app
