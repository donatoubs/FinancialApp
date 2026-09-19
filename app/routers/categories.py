"""
Router para la gestión de Categorías de Ingresos y Gastos.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse
from app.auth.dependencies import get_current_active_user
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["Categorías"])


@router.get(
    "",
    response_model=List[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar categorías disponibles",
    description="Retorna las categorías predeterminadas del sistema y las personalizadas del usuario autenticado."
)
def list_categories(
    category_type: Optional[str] = Query(None, description="Filtrar por tipo: 'expense' o 'income'"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Asegurar que existan las categorías base
    category_service.seed_default_categories(db)
    return category_service.get_categories(db=db, user_id=current_user.id, category_type=category_type)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva categoría personalizada",
    description="Permite al usuario crear categorías a su medida con icono y color personalizado."
)
def create_category(
    category_in: CategoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return category_service.create_category(
        db=db,
        user_id=current_user.id,
        category_in=category_in
    )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar categoría personalizada",
    description="Elimina una categoría personalizada del usuario. Las categorías por defecto no se pueden borrar."
)
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    success = category_service.delete_category(db=db, category_id=category_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo eliminar la categoría (es una categoría del sistema o no existe)."
        )
    return {"message": "Categoría eliminada exitosamente.", "category_id": category_id}
