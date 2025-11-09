from flask import Blueprint, request, jsonify, current_app
from app.schemas.usuarios import UserCreate, UserLogin, UserResponse
from pydantic import ValidationError
import bcrypt
from datetime import datetime, timezone

"""operacion http:
POST - registrar usuario
POST - logearse 
""" 


# Crear blueprint para hacer la API modular
bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/auth/register
    Body: {
        "nombre": "Juan Pérez",
        "email": "juan@email.com",
        "password": "12345678",
        "clase": "user",  // user, empresa, admin
        "nivel": "intermedio"  // opcional
    }
    """
    try:
        user_data = UserCreate(**request.json)
        
        # 2. Verificar si el email ya existe
        existing_user = current_app.db.users.find_one({"email": user_data.email})
        if existing_user:
            return jsonify({"error": "El email ya está registrado"}), 400
        
        # 3. Hashear la contraseña
        hashed_password = bcrypt.hashpw(
            user_data.password.encode('utf-8'), 
            bcrypt.gensalt()
        )
        
        # 4. Preparar documento para MongoDB
        user_dict = user_data.model_dump(exclude_none=True)
        user_dict['password'] = hashed_password.decode('utf-8')
        user_dict['fecha_registro'] = datetime.now(timezone.utc)
        
        # 5. Insertar en MongoDB
        result = current_app.db.users.insert_one(user_dict)
        
        # 6. Devolver respuesta (sin password)
        user_dict['_id'] = str(result.inserted_id)
        user_dict.pop('password')  # No devolver contraseña
        
        user_response = UserResponse(**user_dict)
        
        return jsonify({
            "message": "Usuario registrado exitosamente",
            "user": user_response.model_dump(exclude_none=True)
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Body: {
        "email": "juan@email.com",
        "password": "12345678"
    }
    """
    try:
        # 1. Validar datos con Pydantic
        login_data = UserLogin(**request.json)
        
        # 2. Buscar usuario por email
        user = current_app.db.users.find_one({"email": login_data.email})
        if not user:
            return jsonify({"error": "Credenciales inválidas"}), 401
        
        # 3. Verificar contraseña
        password_match = bcrypt.checkpw(
            login_data.password.encode('utf-8'),
            user['password'].encode('utf-8')
        )
        
        if not password_match:
            return jsonify({"error": "Credenciales inválidas"}), 401
        
        # 4. Login exitoso
        user['_id'] = str(user['_id'])
        user.pop('password')  # No devolver contraseña
        
        user_response = UserResponse(**user)
        
        return jsonify({
            "message": "Login exitoso",
            "user": user_response.model_dump(exclude_none=True)
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": "Datos inválidos", "details": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
