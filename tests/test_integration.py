"""Integration tests for SI-GADES application."""

import pytest
from nicegui.testing import User
from app.database import reset_db
from app.geo_service import GeospatialService
from app.complaint_service import ComplaintService
from app.models import ComplaintCreate
from decimal import Decimal


@pytest.fixture
def new_db():
    """Provide fresh database for each test."""
    reset_db()
    yield
    reset_db()


class TestApplicationIntegration:
    """Test full application integration."""

    async def test_full_application_startup(self, user: User, new_db) -> None:
        """Test that the full application starts up correctly."""
        # Seed the database with default layers
        GeospatialService.seed_default_layers()

        # Application should load
        await user.open("/")

        # Main components should be present
        await user.should_see("SI-GADES")
        await user.should_see("Sistem Infrastruktur Geo Spasial Berbasis Desa")
        await user.should_see("Kontrol Peta")

    def test_services_integration(self, new_db):
        """Test that services work together correctly."""
        # Seed layers
        GeospatialService.seed_default_layers()

        # Get layers
        layers = GeospatialService.get_all_active_layers()
        assert len(layers) > 0

        # Create a complaint
        complaint_data = ComplaintCreate(
            title="Test Integration Complaint",
            description="Testing service integration",
            latitude=Decimal("-8.55"),
            longitude=Decimal("116.15"),
            location_description="Test location",
        )

        complaint = ComplaintService.create_complaint(complaint_data)
        assert complaint is not None

        # Get complaints in area
        complaints = ComplaintService.get_complaints_in_area(south=-8.8, west=115.9, north=-8.3, east=116.4)
        assert len(complaints) == 1
        assert complaints[0].title == "Test Integration Complaint"

    def test_coordinate_validation_integration(self, new_db):
        """Test coordinate validation with West Lombok bounds."""
        # Valid coordinates within West Lombok
        valid_lat, valid_lon = GeospatialService.get_default_map_center()
        assert GeospatialService.validate_coordinates(valid_lat, valid_lon)

        # Create complaint with valid coordinates
        complaint_data = ComplaintCreate(
            title="Valid Location Complaint",
            description="Within bounds",
            latitude=Decimal(str(valid_lat)),
            longitude=Decimal(str(valid_lon)),
        )

        complaint = ComplaintService.create_complaint(complaint_data)
        assert complaint is not None

    async def test_ui_data_integration(self, user: User, new_db) -> None:
        """Test UI integration with database data."""
        # Create some test data
        GeospatialService.seed_default_layers()

        # Create a test complaint
        complaint_data = ComplaintCreate(
            title="UI Test Complaint",
            description="Testing UI integration",
            latitude=Decimal("-8.55"),
            longitude=Decimal("116.15"),
        )
        ComplaintService.create_complaint(complaint_data)

        # Open application
        await user.open("/")

        # Should load with data
        await user.should_see("SI-GADES")

        # Open layer controls
        user.find("Layer Infrastruktur").click()
        await user.should_see("Refresh Layer")

    def test_file_processing_pipeline(self, new_db):
        """Test the file upload and processing pipeline."""
        # Create sample KML content
        kml_content = b'<?xml version="1.0" encoding="UTF-8"?><kml></kml>'

        # Process through the pipeline
        from app.models import FileType

        # Test KML processing
        geom_data = GeospatialService.process_kml_file(kml_content, "test.kml")
        assert geom_data["type"] == "FeatureCollection"

        # Test layer saving
        layer = GeospatialService.save_user_layer(
            file_content=kml_content,
            filename="test.kml",
            file_type=FileType.KML,
            name="Test Integration Layer",
            is_public=True,
        )
        assert layer is not None

        # Verify layer appears in active layers
        layers = GeospatialService.get_all_active_layers()
        user_layers = [layer for layer in layers if layer.layer_type == "user_uploaded"]
        assert len(user_layers) == 1
        assert user_layers[0].name == "Test Integration Layer"

    def test_complaint_workflow_integration(self, new_db):
        """Test the complete complaint workflow."""
        # Setup upload directory
        ComplaintService.setup_upload_dir()

        # Create complaint
        complaint_data = ComplaintCreate(
            title="Workflow Test",
            description="Testing complete workflow",
            latitude=Decimal("-8.55"),
            longitude=Decimal("116.15"),
            submitter_name="Test User",
        )

        complaint = ComplaintService.create_complaint(complaint_data)
        assert complaint is not None
        assert complaint.id is not None

        # Add photo
        photo_content = b"fake image data"
        photo = ComplaintService.add_photo_to_complaint(
            complaint.id, photo_content, "test.jpg", "image/jpeg", "Test photo"
        )
        assert photo is not None

        # Mark as redirected
        success = ComplaintService.mark_redirected(complaint.id, "facebook")
        assert success

        # Verify final state
        result = ComplaintService.get_complaint(complaint.id)
        assert result is not None
        assert len(result.photos) == 1
        assert result.status.value == "redirected"

    def test_geographic_search_integration(self, new_db):
        """Test geographic search functionality."""
        # Create complaints in and out of West Lombok
        west_lombok_complaint = ComplaintCreate(
            title="In West Lombok", description="Within bounds", latitude=Decimal("-8.55"), longitude=Decimal("116.15")
        )

        outside_complaint = ComplaintCreate(
            title="Outside West Lombok",
            description="Outside bounds",
            latitude=Decimal("-7.0"),  # Too far north
            longitude=Decimal("117.0"),  # Too far east
        )

        ComplaintService.create_complaint(west_lombok_complaint)
        ComplaintService.create_complaint(outside_complaint)

        # Search within West Lombok bounds
        bounds = GeospatialService.get_west_lombok_bounds()
        complaints_in_area = ComplaintService.get_complaints_in_area(
            south=bounds["south"], west=bounds["west"], north=bounds["north"], east=bounds["east"]
        )

        # Should only find the one inside West Lombok
        assert len(complaints_in_area) == 1
        assert complaints_in_area[0].title == "In West Lombok"
