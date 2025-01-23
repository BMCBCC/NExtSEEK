# backend/app/api/interactive_table.py

# api/interactive_table.py

from fastapi import APIRouter, HTTPException, Path
from ..services.nhp_service import save_nhp_info_to_json
from ..models.schemas import NHPInfo
from typing import List
router = APIRouter()

@router.get("/{nhp_name}", response_model=List[NHPInfo])
async def get_nhp_info(nhp_name: str = Path(..., min_length=1)):
    try:
        nhp_info = save_nhp_info_to_json(nhp_name, filename="./app/api/data/NHP_info.json")
        if nhp_info:
            return nhp_info
        else:
            raise HTTPException(status_code=404, detail="NHP Info not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
