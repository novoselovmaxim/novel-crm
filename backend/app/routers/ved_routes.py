from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from decimal import Decimal

from ..database import get_db
from ..models_ved import VedDeclaration, VedCompanyProfile
from ..models import Company, User
from ..schemas_ved import (
    VedDeclarationResponse,
    VedProfileResponse,
    VedProfileDetailResponse,
    VedStatsResponse,
    VedImportResponse,
)
from ..auth import get_current_user
from ..import_ved import import_ved_files

router = APIRouter(prefix="/api/ved", tags=["ved"])


@router.get("/profiles", response_model=List[VedProfileResponse])
async def list_profiles(
    direction: Optional[str] = None,
    country: Optional[str] = None,
    hs_code: Optional[str] = None,
    search: Optional[str] = None,
    has_company: Optional[bool] = None,
    sort_by: str = "total_declarations",
    sort_dir: str = "desc",
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(VedCompanyProfile)

    if direction:
        q = q.where(VedCompanyProfile.directions.any(direction))
    if country:
        q = q.where(
            VedCompanyProfile.destination_countries.any(country)
            | VedCompanyProfile.source_countries.any(country)
        )
    if hs_code:
        q = q.where(VedCompanyProfile.hs_codes.any(hs_code))
    if search:
        pattern = f"%{search}%"
        q = q.where(
            VedCompanyProfile.company_name.ilike(pattern)
            | VedCompanyProfile.inn.ilike(pattern)
        )
    if has_company is True:
        q = q.where(VedCompanyProfile.company_id.isnot(None))
    elif has_company is False:
        q = q.where(VedCompanyProfile.company_id.is_(None))

    sort_col = getattr(VedCompanyProfile, sort_by, VedCompanyProfile.total_declarations)
    if sort_dir == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())

    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/profiles/{inn}", response_model=VedProfileDetailResponse)
async def get_profile(
    inn: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VedCompanyProfile).where(VedCompanyProfile.inn == inn)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    decl_result = await db.execute(
        select(VedDeclaration)
        .where(VedDeclaration.inn == inn)
        .order_by(VedDeclaration.declaration_date.desc().nullslast())
        .limit(200)
    )
    declarations = decl_result.scalars().all()

    return VedProfileDetailResponse(
        **{k: v for k, v in profile.__dict__.items() if not k.startswith("_")},
        declarations=declarations,
    )


@router.get("/declarations", response_model=List[VedDeclarationResponse])
async def list_declarations(
    direction: Optional[str] = None,
    inn: Optional[str] = None,
    country: Optional[str] = None,
    hs_code: Optional[str] = None,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(VedDeclaration)

    if direction:
        q = q.where(VedDeclaration.direction == direction)
    if inn:
        q = q.where(VedDeclaration.inn == inn)
    if country:
        q = q.where(
            VedDeclaration.country_from == country
            | VedDeclaration.country_to == country
        )
    if hs_code:
        q = q.where(VedDeclaration.hs_code == hs_code)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            VedDeclaration.company_name.ilike(pattern)
            | VedDeclaration.inn.ilike(pattern)
        )

    q = q.order_by(VedDeclaration.declaration_date.desc().nullslast())
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats", response_model=VedStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_profiles = (await db.execute(select(func.count(VedCompanyProfile.id)))).scalar() or 0
    total_declarations = (await db.execute(select(func.count(VedDeclaration.id)))).scalar() or 0

    with_company = (await db.execute(
        select(func.count(VedCompanyProfile.id)).where(VedCompanyProfile.company_id.isnot(None))
    )).scalar() or 0

    total_cv = (await db.execute(
        select(func.sum(VedCompanyProfile.total_customs_value))
    )).scalar() or 0

    import_count = (await db.execute(
        select(func.count(VedCompanyProfile.id)).where(VedCompanyProfile.directions.any("import"))
    )).scalar() or 0

    export_count = (await db.execute(
        select(func.count(VedCompanyProfile.id)).where(VedCompanyProfile.directions.any("export"))
    )).scalar() or 0

    top_countries_q = await db.execute(
        text("""
            SELECT unnest(destination_countries) as country, COUNT(*) as cnt
            FROM ved_company_profiles
            GROUP BY country
            ORDER BY cnt DESC
            LIMIT 10
        """)
    )
    top_countries = [{"country": r[0], "count": r[1]} for r in top_countries_q.fetchall()]

    top_hs_q = await db.execute(
        text("""
            SELECT unnest(hs_codes) as code, COUNT(*) as cnt
            FROM ved_company_profiles
            GROUP BY code
            ORDER BY cnt DESC
            LIMIT 10
        """)
    )
    top_hs = [{"code": r[0], "count": r[1]} for r in top_hs_q.fetchall()]

    return VedStatsResponse(
        total_profiles=total_profiles,
        total_declarations=total_declarations,
        with_company=with_company,
        without_company=total_profiles - with_company,
        import_count=import_count,
        export_count=export_count,
        total_customs_value=total_cv,
        top_countries=top_countries,
        top_hs_codes=top_hs,
    )


@router.post("/import", response_model=VedImportResponse)
async def import_ved(
    file_paths: List[str],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    try:
        result = await import_ved_files(file_paths)
        return VedImportResponse(status="ok", **result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match-companies")
async def match_companies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(
        select(VedCompanyProfile).where(VedCompanyProfile.company_id.is_(None))
    )
    unmatched = result.scalars().all()

    matched = 0
    for profile in unmatched:
        company_result = await db.execute(
            select(Company.id).where(Company.inn == profile.inn)
        )
        company = company_result.first()
        if company:
            profile.company_id = company[0]
            matched += 1

    await db.commit()
    return {"matched": matched, "checked": len(unmatched)}


@router.post("/link/{inn}")
async def link_profile(
    inn: str,
    company_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    result = await db.execute(
        select(VedCompanyProfile).where(VedCompanyProfile.inn == inn)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile.company_id = company_id
    await db.commit()
    return {"status": "linked"}
