from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import verify_token
from app.services.supabase_client import supabase

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"], dependencies=[Depends(verify_token)])

VALID_TYPES = {"quant", "dividend"}


class ProfileCreate(BaseModel):
    name: str
    analysis_type: str = "quant"


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    analysis_type: Optional[str] = None


@router.get("")
def list_profiles():
    try:
        result = supabase.table("profiles").select("*").order("created_at").execute()
        return {"status": "success", "data": result.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def create_profile(body: ProfileCreate):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="프로필 이름을 입력해 주세요.")
    analysis_type = body.analysis_type if body.analysis_type in VALID_TYPES else "quant"
    try:
        result = supabase.table("profiles").insert({"name": name, "analysis_type": analysis_type}).execute()
        return {"status": "success", "data": result.data[0] if result.data else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{profile_id}")
def update_profile(profile_id: int, body: ProfileUpdate):
    updates: dict = {}
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="프로필 이름을 입력해 주세요.")
        updates["name"] = name
    if body.analysis_type is not None:
        if body.analysis_type not in VALID_TYPES:
            raise HTTPException(status_code=400, detail=f"analysis_type은 {VALID_TYPES} 중 하나여야 합니다.")
        updates["analysis_type"] = body.analysis_type
    if not updates:
        raise HTTPException(status_code=400, detail="변경할 항목이 없습니다.")
    try:
        result = supabase.table("profiles").update(updates).eq("id", profile_id).execute()
        return {"status": "success", "data": result.data[0] if result.data else {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{profile_id}")
def delete_profile(profile_id: int):
    try:
        supabase.table("profiles").delete().eq("id", profile_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
