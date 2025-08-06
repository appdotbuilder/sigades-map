"""Tests for complaint service functionality."""

import pytest
from decimal import Decimal
from app.complaint_service import ComplaintService
from app.models import ComplaintCreate, ComplaintStatus
from app.database import reset_db


@pytest.fixture
def new_db():
    """Provide fresh database for each test."""
    reset_db()
    yield
    reset_db()


class TestComplaintService:
    """Test complaint service operations."""

    def test_setup_upload_dir(self):
        """Test upload directory creation."""
        ComplaintService.setup_upload_dir()
        assert ComplaintService.UPLOAD_DIR.exists()
        assert ComplaintService.UPLOAD_DIR.is_dir()

    def test_create_complaint_basic(self, new_db):
        """Test creating a basic complaint."""
        complaint_data = ComplaintCreate(
            title="Jalan rusak",
            description="Jalan berlubang di depan pasar",
            latitude=Decimal("-8.55"),
            longitude=Decimal("116.15"),
            location_description="Depan pasar tradisional",
        )

        complaint = ComplaintService.create_complaint(complaint_data)

        assert complaint is not None
        assert complaint.title == "Jalan rusak"
        assert complaint.description == "Jalan berlubang di depan pasar"
        assert complaint.latitude == Decimal("-8.55")
        assert complaint.longitude == Decimal("116.15")
        assert complaint.location_description == "Depan pasar tradisional"
        assert complaint.status == ComplaintStatus.SUBMITTED
        assert complaint.submitter_name is None
        assert not complaint.facebook_redirected
        assert not complaint.lapor_redirected

    def test_create_complaint_with_contact(self, new_db):
        """Test creating complaint with contact information."""
        complaint_data = ComplaintCreate(
            title="Lampu jalan mati",
            description="Lampu jalan tidak menyala sejak seminggu",
            latitude=Decimal("-8.60"),
            longitude=Decimal("116.20"),
            location_description="Jalan utama desa",
            submitter_name="Ahmad Zaini",
            submitter_email="ahmad@email.com",
            submitter_phone="081234567890",
        )

        complaint = ComplaintService.create_complaint(complaint_data, submit_ip="192.168.1.100")

        assert complaint is not None
        assert complaint.submitter_name == "Ahmad Zaini"
        assert complaint.submitter_email == "ahmad@email.com"
        assert complaint.submitter_phone == "081234567890"
        assert complaint.submit_ip == "192.168.1.100"

    def test_get_complaint_not_found(self, new_db):
        """Test getting non-existent complaint."""
        result = ComplaintService.get_complaint(999)
        assert result is None

    def test_get_complaint_with_photos(self, new_db):
        """Test getting complaint with photos."""
        # Create complaint
        complaint_data = ComplaintCreate(
            title="Drainase tersumbat",
            description="Saluran air tersumbat sampah",
            latitude=Decimal("-8.50"),
            longitude=Decimal("116.10"),
        )

        complaint = ComplaintService.create_complaint(complaint_data)
        assert complaint is not None
        assert complaint.id is not None

        # Add photos
        photo1_content = b"fake image content 1"
        photo2_content = b"fake image content 2"

        photo1 = ComplaintService.add_photo_to_complaint(
            complaint.id, photo1_content, "photo1.jpg", "image/jpeg", "Foto 1"
        )
        photo2 = ComplaintService.add_photo_to_complaint(
            complaint.id, photo2_content, "photo2.jpg", "image/jpeg", "Foto 2", display_order=1
        )

        assert photo1 is not None
        assert photo2 is not None

        # Get complaint with photos
        result = ComplaintService.get_complaint(complaint.id)
        assert result is not None
        assert len(result.photos) == 2

        # Photos should be ordered by display_order
        assert result.photos[0].caption == "Foto 1"
        assert result.photos[1].caption == "Foto 2"

    def test_add_photo_invalid_type(self, new_db):
        """Test adding photo with invalid MIME type."""
        complaint_data = ComplaintCreate(
            title="Test complaint",
            description="Test description",
            latitude=Decimal("-8.55"),
            longitude=Decimal("116.15"),
        )

        complaint = ComplaintService.create_complaint(complaint_data)
        assert complaint is not None
        assert complaint.id is not None

        # Try to add invalid file type
        result = ComplaintService.add_photo_to_complaint(
            complaint.id, b"fake content", "document.pdf", "application/pdf"
        )

        assert result is None

    def test_add_photo_too_large(self, new_db):
        """Test adding photo that exceeds size limit."""
        complaint_data = ComplaintCreate(
            title="Test complaint",
            description="Test description",
            latitude=Decimal("-8.55"),
            longitude=Decimal("116.15"),
        )

        complaint = ComplaintService.create_complaint(complaint_data)
        assert complaint is not None
        assert complaint.id is not None

        # Create content larger than 5MB
        large_content = b"x" * (6 * 1024 * 1024)

        result = ComplaintService.add_photo_to_complaint(complaint.id, large_content, "large_photo.jpg", "image/jpeg")

        assert result is None

    def test_mark_redirected_facebook(self, new_db):
        """Test marking complaint as redirected to Facebook."""
        complaint_data = ComplaintCreate(
            title="Test complaint",
            description="Test description",
            latitude=Decimal("-8.55"),
            longitude=Decimal("116.15"),
        )

        complaint = ComplaintService.create_complaint(complaint_data)
        assert complaint is not None
        assert complaint.id is not None

        success = ComplaintService.mark_redirected(complaint.id, "facebook")
        assert success

        # Verify status changed
        result = ComplaintService.get_complaint(complaint.id)
        assert result is not None
        assert result.status == ComplaintStatus.REDIRECTED

    def test_mark_redirected_lapor(self, new_db):
        """Test marking complaint as redirected to Lapor."""
        complaint_data = ComplaintCreate(
            title="Test complaint",
            description="Test description",
            latitude=Decimal("-8.55"),
            longitude=Decimal("116.15"),
        )

        complaint = ComplaintService.create_complaint(complaint_data)
        assert complaint is not None
        assert complaint.id is not None

        success = ComplaintService.mark_redirected(complaint.id, "lapor")
        assert success

        # Verify status changed
        result = ComplaintService.get_complaint(complaint.id)
        assert result is not None
        assert result.status == ComplaintStatus.REDIRECTED

    def test_mark_redirected_both_platforms(self, new_db):
        """Test marking complaint as redirected to both platforms."""
        complaint_data = ComplaintCreate(
            title="Test complaint",
            description="Test description",
            latitude=Decimal("-8.55"),
            longitude=Decimal("116.15"),
        )

        complaint = ComplaintService.create_complaint(complaint_data)
        assert complaint is not None
        assert complaint.id is not None

        # Mark as redirected to Facebook
        success1 = ComplaintService.mark_redirected(complaint.id, "facebook")
        assert success1

        # Mark as redirected to Lapor
        success2 = ComplaintService.mark_redirected(complaint.id, "lapor")
        assert success2

        # Should be completed now
        result = ComplaintService.get_complaint(complaint.id)
        assert result is not None
        assert result.status == ComplaintStatus.COMPLETED

    def test_mark_redirected_invalid_complaint(self, new_db):
        """Test marking non-existent complaint as redirected."""
        success = ComplaintService.mark_redirected(999, "facebook")
        assert not success

    def test_get_recent_complaints_empty(self, new_db):
        """Test getting recent complaints when none exist."""
        complaints = ComplaintService.get_recent_complaints()
        assert complaints == []

    def test_get_recent_complaints_with_data(self, new_db):
        """Test getting recent complaints with data."""
        # Create multiple complaints
        for i in range(5):
            complaint_data = ComplaintCreate(
                title=f"Complaint {i + 1}",
                description=f"Description {i + 1}",
                latitude=Decimal("-8.55"),
                longitude=Decimal("116.15"),
            )
            ComplaintService.create_complaint(complaint_data)

        complaints = ComplaintService.get_recent_complaints(3)

        # Should get 3 most recent
        assert len(complaints) == 3

        # Should be ordered by creation time (newest first)
        assert complaints[0].title == "Complaint 5"
        assert complaints[1].title == "Complaint 4"
        assert complaints[2].title == "Complaint 3"

    def test_get_complaints_in_area(self, new_db):
        """Test getting complaints within geographic area."""
        # Create complaints in different locations
        inside_complaint = ComplaintCreate(
            title="Inside complaint", description="Inside area", latitude=Decimal("-8.55"), longitude=Decimal("116.15")
        )

        outside_complaint = ComplaintCreate(
            title="Outside complaint",
            description="Outside area",
            latitude=Decimal("-7.00"),  # Outside West Lombok
            longitude=Decimal("117.00"),
        )

        ComplaintService.create_complaint(inside_complaint)
        ComplaintService.create_complaint(outside_complaint)

        # Search within West Lombok bounds
        complaints = ComplaintService.get_complaints_in_area(south=-8.8, west=115.9, north=-8.3, east=116.4)

        # Should only find the inside complaint
        assert len(complaints) == 1
        assert complaints[0].title == "Inside complaint"

    def test_get_complaints_in_area_empty(self, new_db):
        """Test getting complaints in area with no matches."""
        # Create complaint outside search area
        complaint_data = ComplaintCreate(
            title="Far away complaint", description="Very far", latitude=Decimal("-10.00"), longitude=Decimal("120.00")
        )
        ComplaintService.create_complaint(complaint_data)

        # Search in different area
        complaints = ComplaintService.get_complaints_in_area(south=-8.8, west=115.9, north=-8.3, east=116.4)

        assert complaints == []

    def test_allowed_photo_types(self):
        """Test that allowed photo types are properly defined."""
        allowed_types = ComplaintService.ALLOWED_PHOTO_TYPES

        # Should include common image formats
        assert "image/jpeg" in allowed_types
        assert "image/png" in allowed_types
        assert "image/gif" in allowed_types
        assert "image/webp" in allowed_types

        # Should not include non-image types
        assert "text/plain" not in allowed_types
        assert "application/pdf" not in allowed_types

    def test_max_photo_size_limit(self):
        """Test photo size limit is reasonable."""
        max_size = ComplaintService.MAX_PHOTO_SIZE

        # Should be 5MB (5 * 1024 * 1024 bytes)
        assert max_size == 5 * 1024 * 1024

        # Should be reasonable for mobile uploads
        assert 1024 * 1024 <= max_size <= 10 * 1024 * 1024  # Between 1MB and 10MB
