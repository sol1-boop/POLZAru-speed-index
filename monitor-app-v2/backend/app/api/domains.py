from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from app.core.database import get_db
from app.models import Domain, LighthouseMetric
from app.schemas import DomainCreate, DomainResponse, DomainUpdate, LighthouseMetricResponse
from app.services.lighthouse_service import run_lighthouse_audit

router = APIRouter(prefix="/domains", tags=["Domains"])


async def get_current_user_id():
    """Placeholder for getting current user from JWT token."""
    # TODO: Implement JWT token verification
    return 1


@router.get("/", response_model=List[DomainResponse])
async def get_domains(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Get all domains for the current user."""
    result = await db.execute(
        select(Domain)
        .where(Domain.owner_id == current_user_id)
        .offset(skip)
        .limit(limit)
    )
    domains = result.scalars().all()
    return domains


@router.post("/", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def create_domain(
    domain_data: DomainCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Create a new domain for monitoring."""
    # Check if domain already exists
    result = await db.execute(
        select(Domain).where(Domain.url == str(domain_data.url))
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain already exists"
        )
    
    # Create domain
    new_domain = Domain(
        url=str(domain_data.url),
        name=domain_data.name,
        check_interval=domain_data.check_interval,
        owner_id=current_user_id
    )
    
    db.add(new_domain)
    await db.flush()
    await db.refresh(new_domain)
    
    # Trigger initial Lighthouse audit
    await run_lighthouse_audit(db, new_domain.id)
    
    return new_domain


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(
    domain_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Get a specific domain by ID."""
    result = await db.execute(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.owner_id == current_user_id
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found"
        )
    
    return domain


@router.put("/{domain_id}", response_model=DomainResponse)
async def update_domain(
    domain_id: int,
    domain_data: DomainUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Update a domain."""
    result = await db.execute(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.owner_id == current_user_id
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found"
        )
    
    # Update fields
    update_data = domain_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(domain, field, value)
    
    await db.flush()
    await db.refresh(domain)
    
    return domain


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(
    domain_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Delete a domain."""
    result = await db.execute(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.owner_id == current_user_id
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found"
        )
    
    await db.delete(domain)
    await db.flush()


@router.get("/{domain_id}/metrics", response_model=List[LighthouseMetricResponse])
async def get_domain_metrics(
    domain_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Get latest Lighthouse metrics for a domain."""
    result = await db.execute(
        select(LighthouseMetric)
        .where(LighthouseMetric.domain_id == domain_id)
        .join(Domain)
        .where(Domain.owner_id == current_user_id)
        .order_by(LighthouseMetric.checked_at.desc())
        .limit(limit)
    )
    metrics = result.scalars().all()
    return metrics


@router.post("/{domain_id}/audit")
async def trigger_audit(
    domain_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Trigger a manual Lighthouse audit for a domain."""
    result = await db.execute(
        select(Domain).where(
            Domain.id == domain_id,
            Domain.owner_id == current_user_id
        )
    )
    domain = result.scalar_one_or_none()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found"
        )
    
    # Trigger audit
    await run_lighthouse_audit(db, domain_id)
    
    return {"message": "Audit triggered successfully"}
