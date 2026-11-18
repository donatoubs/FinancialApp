"""
Panel de administración (solo cuentas con is_superuser, definidas por ADMIN_EMAILS).

Por privacidad, el administrador ve datos de las cuentas (nombre, correo, actividad, cantidades)
pero nunca los montos ni el detalle de los movimientos de otras personas.
Toda acción del administrador queda registrada.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.database import get_db
from app.models.account import BankAccount
from app.models.pending import PendingStatus, PendingTransaction
from app.models.security_event import SecurityEvent
from app.models.transaction import Transaction
from app.models.user import User
from app.services import security_events

router = APIRouter(prefix="/admin", tags=["Administración"], dependencies=[Depends(get_current_admin)])


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


@router.get("/overview", summary="Resumen general")
def overview(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    day, week, month = now - timedelta(days=1), now - timedelta(days=7), now - timedelta(days=30)
    count_events = lambda since, *types: (  # noqa: E731
        db.query(func.count(SecurityEvent.id))
        .filter(SecurityEvent.created_at >= since, SecurityEvent.event_type.in_(types)).scalar()
    )
    return {
        "users": {
            "total": db.query(func.count(User.id)).scalar(),
            "active": db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar(),
            "admins": db.query(func.count(User.id)).filter(User.is_superuser.is_(True)).scalar(),
            "new_7d": db.query(func.count(User.id)).filter(User.created_at >= week).scalar(),
            "active_30d": db.query(func.count(User.id)).filter(User.last_login_at >= month).scalar(),
        },
        "data": {
            "transactions": db.query(func.count(Transaction.id)).scalar(),
            "transactions_7d": db.query(func.count(Transaction.id)).filter(Transaction.created_at >= week).scalar(),
            "accounts": db.query(func.count(BankAccount.id)).scalar(),
            "pending": db.query(func.count(PendingTransaction.id))
                         .filter(PendingTransaction.status == PendingStatus.PENDING).scalar(),
        },
        "security_24h": {
            "logins": count_events(day, "login_success", "login_new_ip"),
            "failed_logins": count_events(day, "login_failed"),
            "lockouts": count_events(day, "login_locked"),
            "suspicious": db.query(func.count(SecurityEvent.id))
                            .filter(SecurityEvent.created_at >= day, SecurityEvent.severity != "info").scalar(),
        },
    }


@router.get("/users", summary="Cuentas registradas")
def list_users(
    q: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    tx_count = (
        db.query(Transaction.user_id, func.count(Transaction.id).label("n"))
        .group_by(Transaction.user_id).subquery()
    )
    query = db.query(User, func.coalesce(tx_count.c.n, 0)).outerjoin(tx_count, tx_count.c.user_id == User.id)
    if q:
        like = f"%{q.strip()}%"   # se envía como parámetro: no hay inyección SQL
        query = query.filter(or_(User.email.ilike(like), User.full_name.ilike(like), User.phone.ilike(like)))
    total = query.count()
    rows = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": u.id, "full_name": u.full_name, "email": u.email, "phone": u.phone,
                "is_active": u.is_active, "is_superuser": u.is_superuser,
                "created_at": _iso(u.created_at), "last_login_at": _iso(u.last_login_at),
                "transactions": n,
            }
            for u, n in rows
        ],
    }


def _target(db: Session, user_id: int, admin: User) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="La cuenta no existe.")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes aplicar esta acción a tu propia cuenta.")
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="No se puede aplicar a otra cuenta de administrador.")
    return user


def _admin_action(db: Session, request: Request, admin: User, user: User, event: str) -> None:
    # El evento queda a nombre de la cuenta afectada (lo ve en su historial) e indica qué administrador actuó
    security_events.record(db, request, event, user=user, detail=f"Por {admin.email}", commit=False)


@router.post("/users/{user_id}/deactivate", summary="Desactivar una cuenta (no puede entrar; se cierran sus sesiones)")
def deactivate_user(user_id: int, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = _target(db, user_id, admin)
    user.is_active = False
    user.token_version = (user.token_version or 0) + 1
    _admin_action(db, request, admin, user, "admin_user_deactivated")
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.post("/users/{user_id}/activate", summary="Reactivar una cuenta")
def activate_user(user_id: int, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = _target(db, user_id, admin)
    user.is_active = True
    _admin_action(db, request, admin, user, "admin_user_activated")
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.post("/users/{user_id}/logout", summary="Cerrar todas las sesiones de una cuenta")
def logout_user(user_id: int, request: Request, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    user = _target(db, user_id, admin)
    user.token_version = (user.token_version or 0) + 1
    _admin_action(db, request, admin, user, "admin_user_logout")
    db.commit()
    return {"id": user.id, "ok": True}


@router.get("/events", summary="Registro de actividad")
def list_events(
    severity: Optional[str] = Query(None, pattern="^(info|warning|critical|suspicious)$"),
    user_id: Optional[int] = None,
    q: Optional[str] = Query(None, max_length=100),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(SecurityEvent)
    if severity == "suspicious":
        query = query.filter(SecurityEvent.severity != "info")
    elif severity:
        query = query.filter(SecurityEvent.severity == severity)
    if user_id:
        query = query.filter(SecurityEvent.user_id == user_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(SecurityEvent.email.ilike(like), SecurityEvent.ip.ilike(like)))
    events = query.order_by(SecurityEvent.created_at.desc()).limit(limit).all()
    return [security_events.serialize(e) for e in events]


@router.get("/suspicious-ips", summary="IPs con más eventos sospechosos (últimos 7 días)")
def suspicious_ips(db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = (
        db.query(SecurityEvent.ip, func.count(SecurityEvent.id).label("n"),
                 func.count(func.distinct(SecurityEvent.email)).label("accounts"),
                 func.max(SecurityEvent.created_at).label("last"))
        .filter(SecurityEvent.created_at >= since, SecurityEvent.severity != "info", SecurityEvent.ip.isnot(None))
        .group_by(SecurityEvent.ip).order_by(func.count(SecurityEvent.id).desc()).limit(20).all()
    )
    return [{"ip": ip, "events": n, "accounts": accounts, "last": _iso(last)} for ip, n, accounts, last in rows]
