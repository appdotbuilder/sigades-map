from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum


class LayerType(str, Enum):
    """Types of infrastructure layers"""

    RICE_FIELDS = "rice_fields"
    IRRIGATION = "irrigation"
    REGENCY_ROADS = "regency_roads"
    REGENCY_BOUNDARIES = "regency_boundaries"
    VILLAGE_BOUNDARIES = "village_boundaries"
    USER_UPLOADED = "user_uploaded"


class FileType(str, Enum):
    """Supported geospatial file types"""

    KML = "kml"
    KMZ = "kmz"
    SHP = "shp"


class ComplaintStatus(str, Enum):
    """Status of public complaints"""

    SUBMITTED = "submitted"
    REDIRECTED = "redirected"
    COMPLETED = "completed"


# Static infrastructure layers from BIG data
class StaticLayer(SQLModel, table=True):
    __tablename__ = "static_layers"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    layer_type: LayerType = Field(description="Type of infrastructure layer")
    description: str = Field(default="", max_length=1000)
    source: str = Field(default="BIG", max_length=100, description="Data source (e.g., BIG)")
    geom_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="GeoJSON data")
    style_properties: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Map styling properties")
    is_active: bool = Field(default=True)
    display_order: int = Field(default=0, description="Layer display order")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# User-uploaded geospatial layers
class UserLayer(SQLModel, table=True):
    __tablename__ = "user_layers"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    file_type: FileType = Field(description="Original file type (KML, KMZ, SHP)")
    original_filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500, description="Path to stored file")
    file_size: int = Field(description="File size in bytes")
    geom_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Converted GeoJSON data")
    style_properties: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Map styling properties")
    is_public: bool = Field(default=False, description="Whether layer is visible to other users")
    is_active: bool = Field(default=True)
    upload_ip: Optional[str] = Field(default=None, max_length=45, description="IP address of uploader")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Public complaints with geolocation
class Complaint(SQLModel, table=True):
    __tablename__ = "complaints"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200, description="Complaint title/subject")
    description: str = Field(max_length=2000, description="Detailed complaint description")

    # Geolocation data
    latitude: Decimal = Field(decimal_places=8, description="Latitude coordinate")
    longitude: Decimal = Field(decimal_places=8, description="Longitude coordinate")
    location_description: str = Field(default="", max_length=500, description="Human-readable location description")

    # Contact information (optional)
    submitter_name: Optional[str] = Field(default=None, max_length=100)
    submitter_email: Optional[str] = Field(default=None, max_length=255)
    submitter_phone: Optional[str] = Field(default=None, max_length=20)

    # Metadata
    status: ComplaintStatus = Field(default=ComplaintStatus.SUBMITTED)
    submit_ip: Optional[str] = Field(default=None, max_length=45, description="IP address of submitter")
    facebook_redirected: bool = Field(default=False, description="Whether redirected to Facebook")
    lapor_redirected: bool = Field(default=False, description="Whether redirected to lapor.go.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    photos: List["ComplaintPhoto"] = Relationship(back_populates="complaint")


# Photos attached to complaints
class ComplaintPhoto(SQLModel, table=True):
    __tablename__ = "complaint_photos"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    complaint_id: int = Field(foreign_key="complaints.id")
    filename: str = Field(max_length=255, description="Original filename")
    file_path: str = Field(max_length=500, description="Path to stored photo")
    file_size: int = Field(description="File size in bytes")
    mime_type: str = Field(max_length=100, description="MIME type (e.g., image/jpeg)")
    caption: str = Field(default="", max_length=500, description="Optional photo caption")
    display_order: int = Field(default=0, description="Photo display order")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    complaint: Complaint = Relationship(back_populates="photos")


# Non-persistent schemas for validation and API


class StaticLayerCreate(SQLModel, table=False):
    name: str = Field(max_length=200)
    layer_type: LayerType
    description: str = Field(default="", max_length=1000)
    source: str = Field(default="BIG", max_length=100)
    geom_data: Dict[str, Any] = Field(default={})
    style_properties: Dict[str, Any] = Field(default={})
    display_order: int = Field(default=0)


class StaticLayerUpdate(SQLModel, table=False):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    geom_data: Optional[Dict[str, Any]] = Field(default=None)
    style_properties: Optional[Dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    display_order: Optional[int] = Field(default=None)


class UserLayerCreate(SQLModel, table=False):
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    file_type: FileType
    original_filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int
    geom_data: Dict[str, Any] = Field(default={})
    style_properties: Dict[str, Any] = Field(default={})
    is_public: bool = Field(default=False)


class ComplaintCreate(SQLModel, table=False):
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    latitude: Decimal
    longitude: Decimal
    location_description: str = Field(default="", max_length=500)
    submitter_name: Optional[str] = Field(default=None, max_length=100)
    submitter_email: Optional[str] = Field(default=None, max_length=255)
    submitter_phone: Optional[str] = Field(default=None, max_length=20)


class ComplaintPhotoCreate(SQLModel, table=False):
    complaint_id: int
    filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int
    mime_type: str = Field(max_length=100)
    caption: str = Field(default="", max_length=500)
    display_order: int = Field(default=0)


# Response schemas
class ComplaintResponse(SQLModel, table=False):
    id: int
    title: str
    description: str
    latitude: Decimal
    longitude: Decimal
    location_description: str
    submitter_name: Optional[str]
    status: ComplaintStatus
    created_at: str  # Will be serialized as ISO format string
    photos: List["ComplaintPhotoResponse"] = []


class ComplaintPhotoResponse(SQLModel, table=False):
    id: int
    filename: str
    file_path: str
    mime_type: str
    caption: str
    display_order: int


class LayerResponse(SQLModel, table=False):
    id: int
    name: str
    description: str
    layer_type: str
    is_active: bool
    geom_data: Dict[str, Any]
    style_properties: Dict[str, Any]
    created_at: str  # Will be serialized as ISO format string
