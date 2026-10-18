from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class InquiryCreate(BaseModel):
    name: str
    phone: str
    email: str
    message: str
    property_id: Optional[str] = None

class Property(BaseModel):
    id: str
    name: str
    location: str
    price: int
    type: str
    listing: str
    beds: int
    baths: int
    area: int
    image: str
    badge: Optional[str] = None

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Meridian & Co. real estate API"}

PROPERTIES = [
    {"id":"p1","name":"The Aurelia Residence","location":"Palm Jumeirah, Dubai","price":2850000,"type":"Villa","listing":"Buy","beds":5,"baths":6,"area":4820,"image":"https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=85","badge":"Featured"},
    {"id":"p2","name":"Casa Maris Penthouse","location":"Downtown Dubai","price":1480000,"type":"Apartment","listing":"Buy","beds":3,"baths":3,"area":2180,"image":"https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1200&q=85","badge":"Exclusive"},
    {"id":"p3","name":"The Willow House","location":"Emirates Hills, Dubai","price":9800,"type":"House","listing":"Rent","beds":4,"baths":4,"area":3560,"image":"https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1200&q=85","badge":"New"},
    {"id":"p4","name":"The Atlas Offices","location":"Business Bay, Dubai","price":3200000,"type":"Office","listing":"Buy","beds":0,"baths":2,"area":2950,"image":"https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=85","badge":"Investment"},
    {"id":"p5","name":"Luna Garden Villa","location":"Jumeirah Islands, Dubai","price":12500,"type":"Villa","listing":"Rent","beds":4,"baths":5,"area":4010,"image":"https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=1200&q=85","badge":"Premium"},
    {"id":"p6","name":"The Linden Apartment","location":"Dubai Marina, Dubai","price":890000,"type":"Apartment","listing":"Buy","beds":2,"baths":2,"area":1450,"image":"https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&q=85","badge":"For Sale"},
]

@api_router.get("/properties", response_model=List[Property])
async def get_properties(listing: Optional[str] = None, location: Optional[str] = None, property_type: Optional[str] = None):
    items = PROPERTIES
    if listing and listing != "All": items = [p for p in items if p["listing"] == listing]
    if location: items = [p for p in items if location.lower() in p["location"].lower()]
    if property_type and property_type != "Any type": items = [p for p in items if p["type"] == property_type]
    return items

@api_router.get("/properties/{property_id}", response_model=Property)
async def get_property(property_id: str):
    item = next((p for p in PROPERTIES if p["id"] == property_id), None)
    if not item: raise HTTPException(status_code=404, detail="Property not found")
    return item

@api_router.post("/inquiries")
async def create_inquiry(input: InquiryCreate):
    doc = input.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.inquiries.insert_one(doc)
    return {"success": True, "message": "Thank you — our property advisor will be in touch shortly."}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    # Exclude MongoDB's _id field from the query results
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()