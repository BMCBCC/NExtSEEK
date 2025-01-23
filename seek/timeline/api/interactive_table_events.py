from fastapi import APIRouter, HTTPException, Path
from ..services.timeline_service import get_event_data
from ..models.schemas import TimelineEvent
from typing import List

router = APIRouter()

# Fetch event data for a specific NHP, event type, and date
@router.get("/{nhp_name}/{event_type}/{date}", response_model=List[TimelineEvent])
async def fetch_event_data(nhp_name: str = Path(..., min_length=1), event_type: str = Path(..., min_length=1), date: str = Path(..., min_length=1)):
    if not nhp_name:
        raise HTTPException(status_code=404, detail="NHP data not found")
    try:
        # print(nhp_name, event_type, date)
        event_data = get_event_data(nhp_name, event_type, date)
        return event_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))