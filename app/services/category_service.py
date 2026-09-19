"""
Servicio de negocio para la gestión de Categorías de Ingresos y Gastos.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.category import Category
from app.schemas.category import CategoryCreate

# Catálogo de categorías predeterminadas del sistema
DEFAULT_CATEGORIES = [
    # Gastos
    {"name": "Alimentación y Supermercado", "icon": "bi-cart3", "color": "#10b981", "type": "expense"},
    {"name": "Transporte y Gasolina", "icon": "bi-car-front", "color": "#0284c7", "type": "expense"},
    {"name": "Vivienda y Alquiler", "icon": "bi-house", "color": "#0ea5e9", "type": "expense"},
    {"name": "Servicios Básicos (Luz, Agua, Internet)", "icon": "bi-lightning-charge", "color": "#f97316", "type": "expense"},
    {"name": "Salud y Medicinas", "icon": "bi-heart-pulse", "color": "#ef4444", "type": "expense"},
    {"name": "Educación y Cursos", "icon": "bi-mortarboard", "color": "#f59e0b", "type": "expense"},
    {"name": "Entretenimiento y Ocio", "icon": "bi-controller", "color": "#8b5cf6", "type": "expense"},
    {"name": "Compras y Ropa", "icon": "bi-bag-check", "color": "#ec4899", "type": "expense"},
    {"name": "Suscripciones (Netflix, Spotify)", "icon": "bi-tv", "color": "#6366f1", "type": "expense"},
    {"name": "Restaurantes y Salidas", "icon": "bi-cup-hot", "color": "#d97706", "type": "expense"},
    {"name": "Otros Gastos", "icon": "bi-tags", "color": "#64748b", "type": "expense"},
    
    # Ingresos
    {"name": "Sueldo y Nómina", "icon": "bi-cash-coin", "color": "#16a34a", "type": "income"},
    {"name": "Ventas y Negocio", "icon": "bi-shop", "color": "#059669", "type": "income"},
    {"name": "Inversiones y Rendimientos", "icon": "bi-graph-up-arrow", "color": "#0d9488", "type": "income"},
    {"name": "Otros Ingresos", "icon": "bi-wallet2", "color": "#14b8a6", "type": "income"},
]


def seed_default_categories(db: Session) -> None:
    """
    Inserta las categorías predeterminadas del sistema si aún no existen en la base de datos.
    """
    existing_count = db.query(Category).filter(Category.is_default.is_(True)).count()
    if existing_count == 0:
        for cat in DEFAULT_CATEGORIES:
            db_cat = Category(
                user_id=None,
                name=cat["name"],
                icon=cat["icon"],
                color=cat["color"],
                category_type=cat["type"],
                is_default=True
            )
            db.add(db_cat)
        db.commit()


def get_categories(
    db: Session,
    user_id: int,
    category_type: Optional[str] = None
) -> List[Category]:
    """
    Retorna las categorías disponibles para el usuario (predeterminadas + creadas por él).
    """
    query = db.query(Category).filter(
        or_(Category.user_id == user_id, Category.is_default.is_(True))
    )
    if category_type:
        query = query.filter(
            or_(Category.category_type == category_type, Category.category_type == "both")
        )
    return query.order_by(Category.is_default.desc(), Category.name.asc()).all()


def get_category_by_id(db: Session, category_id: int, user_id: int) -> Optional[Category]:
    """
    Busca una categoría por ID verificando que sea accesible para el usuario.
    """
    return db.query(Category).filter(
        Category.id == category_id,
        or_(Category.user_id == user_id, Category.is_default.is_(True))
    ).first()


def create_category(db: Session, user_id: int, category_in: CategoryCreate) -> Category:
    """
    Crea una categoría personalizada para el usuario.
    """
    db_cat = Category(
        user_id=user_id,
        name=category_in.name.strip(),
        icon=category_in.icon.strip(),
        color=category_in.color,
        category_type=category_in.category_type,
        is_default=False
    )
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat


def delete_category(db: Session, category_id: int, user_id: int) -> bool:
    """
    Elimina una categoría personalizada del usuario. Las categorías predeterminadas no se pueden borrar.
    """
    cat = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == user_id,
        Category.is_default.is_(False)
    ).first()
    if not cat:
        return False

    db.delete(cat)
    db.commit()
    return True
