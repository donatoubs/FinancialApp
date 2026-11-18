"""
Servicio de negocio para la gestión de Categorías de Ingresos y Gastos.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.category import Category
from app.schemas.category import CategoryCreate

# Catálogo de categorías predeterminadas del sistema.
# Colores: grises carbón (gastos) y verdes (ingresos), acordes a la paleta de la app;
# el naranja queda reservado para avisos.
DEFAULT_CATEGORIES = [
    # Gastos
    {"name": "Alimentación y Supermercado", "icon": "bi-cart3", "color": "#2B2E32", "type": "expense"},
    {"name": "Transporte y Gasolina", "icon": "bi-car-front", "color": "#4A5058", "type": "expense"},
    {"name": "Vivienda y Alquiler", "icon": "bi-house", "color": "#5E6670", "type": "expense"},
    {"name": "Servicios Básicos (Luz, Agua, Internet)", "icon": "bi-lightning-charge", "color": "#737C86", "type": "expense"},
    {"name": "Salud y Medicinas", "icon": "bi-heart-pulse", "color": "#3A3F45", "type": "expense"},
    {"name": "Educación y Cursos", "icon": "bi-mortarboard", "color": "#88909A", "type": "expense"},
    {"name": "Entretenimiento y Ocio", "icon": "bi-controller", "color": "#545B63", "type": "expense"},
    {"name": "Compras y Ropa", "icon": "bi-bag-check", "color": "#6A727C", "type": "expense"},
    {"name": "Suscripciones (Netflix, Spotify)", "icon": "bi-tv", "color": "#40464D", "type": "expense"},
    {"name": "Restaurantes y Salidas", "icon": "bi-cup-hot", "color": "#7D8892", "type": "expense"},
    {"name": "Otros Gastos", "icon": "bi-tags", "color": "#A3ABB3", "type": "expense"},
    
    # Ingresos
    {"name": "Sueldo y Nómina", "icon": "bi-cash-coin", "color": "#2E6B3F", "type": "income"},
    {"name": "Ventas y Negocio", "icon": "bi-shop", "color": "#3F7D50", "type": "income"},
    {"name": "Inversiones y Rendimientos", "icon": "bi-graph-up-arrow", "color": "#558F66", "type": "income"},
    {"name": "Otros Ingresos", "icon": "bi-wallet2", "color": "#6FA07D", "type": "income"},
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
        return

    # Mantener sincronizados los colores de las categorías del sistema ya existentes
    palette = {cat["name"]: cat["color"] for cat in DEFAULT_CATEGORIES}
    changed = False
    for cat in db.query(Category).filter(Category.is_default.is_(True)).all():
        new_color = palette.get(cat.name)
        if new_color and cat.color != new_color:
            cat.color = new_color
            changed = True
    if changed:
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
