from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base, engine, get_db
from app.reconciliation import reconcile
from app.security import authenticate, create_token, require_roles


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Payment Reconciliation API",
    description="Matches payment records against bank settlement data and reports exceptions.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/token", response_model=schemas.TokenOut, tags=["auth"])
def token(form: OAuth2PasswordRequestForm = Depends()) -> schemas.TokenOut:
    roles = authenticate(form.username, form.password)
    if roles is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    return schemas.TokenOut(access_token=create_token(form.username, roles))


@app.post("/reconciliation/payments", response_model=schemas.LoadResult,
          status_code=status.HTTP_201_CREATED, tags=["reconciliation"])
def load_payments(body: schemas.BulkPayments, db: Session = Depends(get_db),
                  _: dict = Depends(require_roles("operator"))) -> schemas.LoadResult:
    db.add_all(models.Payment(**item.model_dump()) for item in body.items)
    db.commit()
    return schemas.LoadResult(loaded=len(body.items))


@app.post("/reconciliation/settlements", response_model=schemas.LoadResult,
          status_code=status.HTTP_201_CREATED, tags=["reconciliation"])
def load_settlements(body: schemas.BulkSettlements, db: Session = Depends(get_db),
                     _: dict = Depends(require_roles("operator"))) -> schemas.LoadResult:
    db.add_all(models.Settlement(**item.model_dump()) for item in body.items)
    db.commit()
    return schemas.LoadResult(loaded=len(body.items))


@app.post("/reconciliation/runs", response_model=schemas.RunSummary, tags=["reconciliation"])
def run_reconciliation(db: Session = Depends(get_db),
                       _: dict = Depends(require_roles())) -> schemas.RunSummary:
    """Admin only: reconcile every payment against every settlement and store the exceptions."""
    payments = db.scalars(select(models.Payment)).all()
    settlements = db.scalars(select(models.Settlement)).all()
    result = reconcile(list(payments), list(settlements))

    run = models.ReconciliationRun(matched=result.matched, exceptions=len(result.findings))
    db.add(run)
    db.flush()
    db.add_all(models.ReconciliationException(run_id=run.id, reference=f.reference, status=f.status,
                                              detail=f.detail) for f in result.findings)
    db.commit()

    S = models.ExceptionStatus
    return schemas.RunSummary(
        run_id=run.id,
        matched=result.matched,
        missing_settlement=result.count(S.MISSING_SETTLEMENT),
        orphan_settlement=result.count(S.ORPHAN_SETTLEMENT),
        amount_mismatch=result.count(S.AMOUNT_MISMATCH),
        duplicate_transaction=result.count(S.DUPLICATE_TRANSACTION),
    )


@app.get("/reconciliation/exceptions", response_model=schemas.ExceptionPage, tags=["reconciliation"])
def list_exceptions(
    status_filter: models.ExceptionStatus | None = Query(None, alias="status"),
    run_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles("analyst")),
) -> schemas.ExceptionPage:
    query = select(models.ReconciliationException)
    if status_filter is not None:
        query = query.where(models.ReconciliationException.status == status_filter)
    if run_id is not None:
        query = query.where(models.ReconciliationException.run_id == run_id)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(models.ReconciliationException.id)
                      .offset((page - 1) * size).limit(size)).all()
    return schemas.ExceptionPage(items=[schemas.ExceptionOut.model_validate(r) for r in rows],
                                 total=total, page=page, size=size)
