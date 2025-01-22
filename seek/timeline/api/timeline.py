# backend/app/api/timeline.py

from fastapi import APIRouter, HTTPException, Path
from ..services.timeline_service import run_All
from ..models.schemas import TimelineEvent
from typing import List

router = APIRouter()

@router.get("/{nhp_name}", response_model=List[TimelineEvent])
async def get_nhp_data(nhp_name: str = Path(..., min_length=1)):
    try:
        timeline_data = run_All(nhp_name)
        if timeline_data:
            return timeline_data
        else:
            raise HTTPException(status_code=404, detail="NHP data not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

