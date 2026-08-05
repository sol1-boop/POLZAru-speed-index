from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models import Domain, LighthouseMetric
from app.schemas import DomainCreate, DomainUpdate, DomainResponse, LighthouseMetricResponse, DashboardSummary
from app.services.auth import get_current_user
from app.workers.tasks import run_lighthouse_audit_task

router = APIRouter(prefix="/domains", tags=["Domains"])


@router.get("/", response_model=List[DomainResponse])
async def get_domains(
    skip: int = 0,
    limit: int = 100,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all domains for current user."""
    result = await db.execute(
        select(Domain)
        .where(Domain.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    domains = result.scalars().all()
    return domains


@router.post("/", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def create_domain(
    domain_data: DomainCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new domain to monitor."""
    # Check if URL already exists for this user
    result = await db.execute(
        select(Domain).where(
            Domain.url == str(domain_data.url),
            Domain.owner_id == current_user.id
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain with this URL already exists",
        )
    
    # Create domain
    new_domain = Domain(
        url=str(domain_data.url),
        name=domain_data.name,
        owner_id=current_user.id,
        check_interval_minutes=domain_data.check_interval_minutes,
    )
    
    db.add(new_domain)
    await db.commit()
    await db.refresh(new_domain)
    
    # Queue initial lighthouse check
    run_lighthouse_audit_task.delay(new_domain.id, new_domain.url)
    
    return new_domain


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(
    domain_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific domain."""
    result = await db.execute(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.owner_id == current_user.id
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )
    
    return domain


@router.put("/{domain_id}", response_model=DomainResponse)
async def update_domain(
    domain_id: int,
    domain_data: DomainUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a domain."""
    result = await db.execute(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.owner_id == current_user.id
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )
    
    # Update fields
    update_data = domain_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(domain, field, value)
    
    await db.commit()
    await db.refresh(domain)
    
    return domain


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    domain_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a domain."""
    result = await db.execute(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.owner_id == current_user.id
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )
    
    await db.delete(domain)
    await db.commit()
    
    return None


@router.get("/{domain_id}/metrics", response_model=List[LighthouseMetricResponse])
async def get_domain_metrics(
    domain_id: int,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get latest Lighthouse metrics for a domain."""
    # Verify ownership
    domain_result = await db.execute(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.owner_id == current_user.id
        )
    )
    domain = domain_result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )
    
    # Get metrics
    metrics_result = await db.execute(
        select(LighthouseMetric)
        .where(LighthouseMetric.domain_id == domain_id)
        .order_by(LighthouseMetric.checked_at.desc())
        .limit(limit)
    )
    metrics = metrics_result.scalars().all()
    
    return metrics


@router.post("/{domain_id}/check", status_code=status.HTTP_202_ACCEPTED)
async def trigger_domain_check(
    domain_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a Lighthouse check for a domain."""
    result = await db.execute(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.owner_id == current_user.id
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found",
        )
    
    # Queue check
    run_lighthouse_audit_task.delay(domain.id, domain.url)
    
    return {"status": "queued", "domain_id": domain.id}
