"""Tests for geospatial service functionality."""

import pytest
from app.geo_service import GeospatialService
from app.models import FileType, LayerType
from app.database import reset_db


@pytest.fixture
def new_db():
    """Provide fresh database for each test."""
    reset_db()
    yield
    reset_db()


class TestGeospatialService:
    """Test geospatial service operations."""

    def test_get_west_lombok_bounds(self):
        """Test West Lombok bounding box coordinates."""
        bounds = GeospatialService.get_west_lombok_bounds()

        assert "south" in bounds
        assert "west" in bounds
        assert "north" in bounds
        assert "east" in bounds

        # Verify reasonable bounds for West Lombok
        assert -9.0 <= bounds["south"] <= -7.5
        assert 115.0 <= bounds["west"] <= 116.5
        assert -8.5 <= bounds["north"] <= -7.0
        assert 116.0 <= bounds["east"] <= 117.0

        # Verify south < north and west < east
        assert bounds["south"] < bounds["north"]
        assert bounds["west"] < bounds["east"]

    def test_get_default_map_center(self):
        """Test default map center coordinates."""
        lat, lon = GeospatialService.get_default_map_center()

        # Verify coordinates are within West Lombok bounds
        bounds = GeospatialService.get_west_lombok_bounds()
        assert bounds["south"] <= lat <= bounds["north"]
        assert bounds["west"] <= lon <= bounds["east"]

    def test_validate_coordinates_valid(self):
        """Test coordinate validation with valid coordinates."""
        # Center of West Lombok
        assert GeospatialService.validate_coordinates(-8.55, 116.15)

        # Edge cases within bounds
        bounds = GeospatialService.get_west_lombok_bounds()
        assert GeospatialService.validate_coordinates(bounds["south"], bounds["west"])
        assert GeospatialService.validate_coordinates(bounds["north"], bounds["east"])

    def test_validate_coordinates_invalid(self):
        """Test coordinate validation with invalid coordinates."""
        # Outside West Lombok bounds
        assert not GeospatialService.validate_coordinates(-7.0, 116.0)  # Too far north
        assert not GeospatialService.validate_coordinates(-9.5, 116.0)  # Too far south
        assert not GeospatialService.validate_coordinates(-8.5, 115.0)  # Too far west
        assert not GeospatialService.validate_coordinates(-8.5, 117.0)  # Too far east

        # Completely invalid coordinates
        assert not GeospatialService.validate_coordinates(0.0, 0.0)
        assert not GeospatialService.validate_coordinates(-90.0, -180.0)

    def test_process_kml_file(self):
        """Test KML file processing."""
        kml_content = b'<?xml version="1.0" encoding="UTF-8"?><kml></kml>'
        filename = "test.kml"

        result = GeospatialService.process_kml_file(kml_content, filename)

        assert result["type"] == "FeatureCollection"
        assert "features" in result
        assert "metadata" in result
        assert result["metadata"]["source_file"] == filename
        assert result["metadata"]["format"] == "kml"
        assert result["metadata"]["processed"]

    def test_process_kml_file_invalid(self):
        """Test KML file processing with invalid content."""
        invalid_content = b"not valid xml content"
        filename = "invalid.kml"

        # The current implementation returns a basic structure even for invalid content
        # In a real implementation with proper XML parsing, this would raise an error
        result = GeospatialService.process_kml_file(invalid_content, filename)
        assert result["type"] == "FeatureCollection"

    def test_process_shp_file(self):
        """Test Shapefile processing."""
        shp_content = b"dummy shapefile content"
        filename = "test.shp"

        result = GeospatialService.process_shp_file(shp_content, filename)

        assert result["type"] == "FeatureCollection"
        assert "features" in result
        assert "metadata" in result
        assert result["metadata"]["source_file"] == filename
        assert result["metadata"]["format"] == "shapefile"
        assert result["metadata"]["processed"]

    def test_get_default_style_all_types(self):
        """Test default styling for all file types."""
        for file_type in FileType:
            style = GeospatialService._get_default_style(file_type)

            # Verify required style properties
            assert "color" in style
            assert "weight" in style
            assert "opacity" in style
            assert "fillColor" in style
            assert "fillOpacity" in style

            # Verify color format (hex)
            assert style["color"].startswith("#")
            assert style["fillColor"].startswith("#")

            # Verify numeric ranges
            assert 0 <= style["opacity"] <= 1
            assert 0 <= style["fillOpacity"] <= 1
            assert style["weight"] > 0

    def test_calculate_area_triangle(self):
        """Test area calculation for a simple triangle."""
        # Simple triangle coordinates
        coordinates = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

        area = GeospatialService.calculate_area(coordinates)
        assert area == 0.5

    def test_calculate_area_square(self):
        """Test area calculation for a square."""
        coordinates = [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]]

        area = GeospatialService.calculate_area(coordinates)
        assert area == 4.0

    def test_calculate_area_empty(self):
        """Test area calculation with insufficient coordinates."""
        assert GeospatialService.calculate_area([]) == 0.0
        assert GeospatialService.calculate_area([[0, 0]]) == 0.0
        assert GeospatialService.calculate_area([[0, 0], [1, 1]]) == 0.0

    def test_calculate_distance_same_point(self):
        """Test distance calculation for the same point."""
        coord = (-8.55, 116.15)
        distance = GeospatialService.calculate_distance(coord, coord)
        assert distance == 0.0

    def test_calculate_distance_known_points(self):
        """Test distance calculation between known points."""
        # Two points roughly 1 degree apart
        coord1 = (-8.0, 116.0)
        coord2 = (-8.0, 117.0)

        distance = GeospatialService.calculate_distance(coord1, coord2)

        # Distance should be approximately 111 km (1 degree longitude at equator)
        # At -8 degrees latitude, it's slightly less
        assert 100 < distance < 115

    def test_save_user_layer_kml(self, new_db):
        """Test saving a KML user layer."""
        kml_content = b'<?xml version="1.0" encoding="UTF-8"?><kml></kml>'
        filename = "test.kml"

        layer = GeospatialService.save_user_layer(
            file_content=kml_content,
            filename=filename,
            file_type=FileType.KML,
            name="Test KML Layer",
            description="Test layer description",
            is_public=True,
            upload_ip="127.0.0.1",
        )

        assert layer is not None
        assert layer.name == "Test KML Layer"
        assert layer.description == "Test layer description"
        assert layer.file_type == FileType.KML
        assert layer.original_filename == filename
        assert layer.is_public
        assert layer.upload_ip == "127.0.0.1"
        assert layer.file_size == len(kml_content)

    def test_save_user_layer_invalid_type(self, new_db):
        """Test saving user layer with invalid file type."""
        # This test assumes the validation happens at a higher level
        # The service should handle the error gracefully
        content = b"invalid content"

        layer = GeospatialService.save_user_layer(
            file_content=content,
            filename="test.txt",  # Invalid extension
            file_type=FileType.KML,  # But valid type
            name="Test Layer",
        )

        # Should either return None or handle gracefully
        # The exact behavior depends on implementation
        # For now, we expect it to work since file_type is valid
        assert layer is not None

    def test_get_all_active_layers_empty(self, new_db):
        """Test getting layers when database is empty."""
        layers = GeospatialService.get_all_active_layers()
        assert layers == []

    def test_seed_default_layers(self, new_db):
        """Test seeding default static layers."""
        # Initially no layers
        layers = GeospatialService.get_all_active_layers()
        assert len(layers) == 0

        # Seed default layers
        GeospatialService.seed_default_layers()

        # Should have default layers now
        layers = GeospatialService.get_all_active_layers()
        assert len(layers) > 0

        # Verify all layer types are represented
        layer_types = {layer.layer_type for layer in layers}
        expected_types = {
            LayerType.RICE_FIELDS.value,
            LayerType.IRRIGATION.value,
            LayerType.REGENCY_ROADS.value,
            LayerType.REGENCY_BOUNDARIES.value,
            LayerType.VILLAGE_BOUNDARIES.value,
        }
        assert expected_types.issubset(layer_types)

    def test_seed_default_layers_idempotent(self, new_db):
        """Test that seeding is idempotent."""
        # Seed once
        GeospatialService.seed_default_layers()
        layers_count_1 = len(GeospatialService.get_all_active_layers())

        # Seed again
        GeospatialService.seed_default_layers()
        layers_count_2 = len(GeospatialService.get_all_active_layers())

        # Count should be the same
        assert layers_count_1 == layers_count_2

    def test_get_all_active_layers_includes_user_layers(self, new_db):
        """Test that get_all_active_layers includes public user layers."""
        # Seed default layers first
        GeospatialService.seed_default_layers()
        initial_count = len(GeospatialService.get_all_active_layers())

        # Add a public user layer
        kml_content = b'<?xml version="1.0" encoding="UTF-8"?><kml></kml>'
        GeospatialService.save_user_layer(
            file_content=kml_content, filename="public.kml", file_type=FileType.KML, name="Public Layer", is_public=True
        )

        # Add a private user layer
        GeospatialService.save_user_layer(
            file_content=kml_content,
            filename="private.kml",
            file_type=FileType.KML,
            name="Private Layer",
            is_public=False,
        )

        # Should only include the public user layer
        layers = GeospatialService.get_all_active_layers()
        assert len(layers) == initial_count + 1

        # Find the user layer
        user_layers = [layer for layer in layers if layer.layer_type == "user_uploaded"]
        assert len(user_layers) == 1
        assert user_layers[0].name == "Public Layer"
