"""
Servicio de negocio para la gestión de usuarios: registro, búsqueda, autenticación y actualización.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from fastapi import HTTPException, status
from app.auth.security import burn_password_check, get_password_hash, verify_password


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Busca un usuario por su clave primaria ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Busca un usuario por su correo electrónico (normalizado a minúsculas)."""
    return db.query(User).filter(User.email == email.strip().lower()).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    """
    Crea un nuevo usuario en la base de datos con contraseña hasheada.
    """
    db_user = User(
        email=user_in.email.strip().lower(),
        hashed_password=get_password_hash(user_in.password),
        full_name=" ".join(user_in.full_name.split()),
        phone=user_in.phone,
        currency_preference=user_in.currency_preference.upper(),
        is_active=True,
        is_superuser=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Verifica las credenciales del usuario. Retorna la entidad User si son válidas, o None.
    """
    user = get_user_by_email(db, email)
    if not user:
        burn_password_check(password)   # mismo tiempo de respuesta exista o no el correo
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    """
    Actualiza la información de perfil o contraseña del usuario.
    """
    if user_in.full_name is not None:
        user.full_name = user_in.full_name.strip()
    if user_in.phone is not None:
        user.phone = user_in.phone.strip() or None
    if user_in.currency_preference is not None:
        user.currency_preference = user_in.currency_preference.upper()
    if user_in.password is not None and user_in.password.strip():
        # Cambiar la contraseña exige la actual: una sesión abierta no basta
        if not user_in.current_password or not verify_password(user_in.current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña actual no es correcta.")
        user.hashed_password = get_password_hash(user_in.password)
        user.token_version = (user.token_version or 0) + 1   # cierra las demás sesiones

    db.commit()
    db.refresh(user)
    return user
