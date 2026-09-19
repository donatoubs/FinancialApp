"""
Router de Autenticación y Gestión de Usuarios: Registro, Login, Swagger-Login y Perfil (Me).
Protegido con Limitador de Tasa de Peticiones (Rate Limiting).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserUpdate,
    UserResponse,
    UserAuthResponse
)
from app.auth.security import create_access_token
from app.auth.dependencies import get_current_active_user
from app.services import user_service
from app.security.rate_limiter import auth_rate_limiter

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/register",
    response_model=UserAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    description="Crea una nueva cuenta de usuario con contraseña cifrada y retorna un token JWT inicial."
)
def register(
    request: Request,
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    # Protección de rate limiting
    auth_rate_limiter.check(request)

    # Verificar si el correo ya está en uso
    existing_user = user_service.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya se encuentra registrado."
        )

    # Crear usuario
    user = user_service.create_user(db, user_in)

    # Generar token JWT de acceso
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return UserAuthResponse(
        user=user,
        token=Token(access_token=access_token, token_type="bearer"),
        message="Usuario registrado exitosamente."
    )


@router.post(
    "/login",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión (JSON)",
    description="Autentica las credenciales del usuario y retorna un token JWT junto con su perfil."
)
def login_json(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    # Protección de rate limiting contra fuerza bruta
    auth_rate_limiter.check(request)

    user = user_service.authenticate_user(db, email=credentials.email, password=credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario está inactiva."
        )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return UserAuthResponse(
        user=user,
        token=Token(access_token=access_token, token_type="bearer"),
        message="Inicio de sesión exitoso."
    )


@router.post(
    "/swagger-login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Login para Swagger UI (OAuth2 Form)",
    description="Endpoint estándar de OAuth2 con datos de formulario para compatibilidad con el botón 'Authorize' de Swagger UI."
)
def login_swagger(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    auth_rate_limiter.check(request)

    user = user_service.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo."
        )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener perfil del usuario autenticado",
    description="Retorna la información del perfil del usuario validando el token JWT recibido en la cabecera."
)
def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar perfil del usuario autenticado",
    description="Permite modificar el nombre completo o la moneda de preferencia del usuario."
)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return user_service.update_user(db=db, user=current_user, user_in=user_update)
