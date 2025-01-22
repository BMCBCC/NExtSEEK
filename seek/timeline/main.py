# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import interactive_table, timeline, interactive_table_events

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interactive_table.router, prefix="/nhp_info")
app.include_router(timeline.router, prefix="/nhp_data")
app.include_router(interactive_table_events.router, prefix="/event_data")
