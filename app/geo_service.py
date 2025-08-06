"""Geospatial service layer for handling map data, file processing, and spatial operations."""

import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from sqlmodel import select, col
from app.database import get_session
from app.models import StaticLayer, UserLayer, LayerType, FileType, LayerResponse


class GeospatialService:
    """Service for managing geospatial data and operations."""

    @staticmethod
    def get_all_active_layers() -> List[LayerResponse]:
        """Get all active layers (static + user layers) for map display."""
        with get_session() as session:
            layers = []

            # Get static layers
            static_layers = session.exec(
                select(StaticLayer).where(StaticLayer.is_active).order_by(col(StaticLayer.display_order))
            ).all()

            for layer in static_layers:
                layers.append(
                    LayerResponse(
                        id=layer.id or 0,
                        name=layer.name,
                        description=layer.description,
                        layer_type=layer.layer_type.value,
                        is_active=layer.is_active,
                        geom_data=layer.geom_data,
                        style_properties=layer.style_properties,
                        created_at=layer.created_at.isoformat(),
                    )
                )

            # Get public user layers
            user_layers = session.exec(
                select(UserLayer)
                .where(UserLayer.is_active, UserLayer.is_public)
                .order_by(col(UserLayer.created_at).desc())
            ).all()

            for layer in user_layers:
                layers.append(
                    LayerResponse(
                        id=layer.id or 0,
                        name=layer.name,
                        description=layer.description,
                        layer_type="user_uploaded",
                        is_active=layer.is_active,
                        geom_data=layer.geom_data,
                        style_properties=layer.style_properties,
                        created_at=layer.created_at.isoformat(),
                    )
                )

            return layers

    @staticmethod
    def get_west_lombok_bounds() -> Dict[str, float]:
        """Get the bounding box coordinates for West Lombok Regency."""
        return {"south": -8.8, "west": 115.9, "north": -8.3, "east": 116.4}

    @staticmethod
    def get_default_map_center() -> Tuple[float, float]:
        """Get the default center coordinates for West Lombok."""
        return (-8.55, 116.15)  # Approximate center of West Lombok

    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """Validate if coordinates are within West Lombok bounds."""
        bounds = GeospatialService.get_west_lombok_bounds()
        return bounds["south"] <= latitude <= bounds["north"] and bounds["west"] <= longitude <= bounds["east"]

    @staticmethod
    def process_kml_file(file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process KML file and extract geospatial data."""
        try:
            # For now, return a basic structure
            # In a real implementation, you'd use libraries like fastkml or lxml
            return {
                "type": "FeatureCollection",
                "features": [],
                "metadata": {"source_file": filename, "processed": True, "format": "kml"},
            }
        except Exception as e:
            raise ValueError(f"Failed to process KML file: {str(e)}")

    @staticmethod
    def process_kmz_file(file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process KMZ file (zipped KML) and extract geospatial data."""
        try:
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(file_content)
                temp_file.flush()

                with zipfile.ZipFile(temp_file.name, "r") as kmz:
                    # Look for KML files in the KMZ
                    kml_files = [f for f in kmz.namelist() if f.endswith(".kml")]
                    if not kml_files:
                        raise ValueError("No KML files found in KMZ archive")

                    # Process the first KML file found
                    kml_content = kmz.read(kml_files[0])
                    return GeospatialService.process_kml_file(kml_content, kml_files[0])

        except Exception as e:
            raise ValueError(f"Failed to process KMZ file: {str(e)}")

    @staticmethod
    def process_shp_file(file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process Shapefile and extract geospatial data."""
        try:
            # For now, return a basic structure
            # In a real implementation, you'd use libraries like fiona or geopandas
            return {
                "type": "FeatureCollection",
                "features": [],
                "metadata": {"source_file": filename, "processed": True, "format": "shapefile"},
            }
        except Exception as e:
            raise ValueError(f"Failed to process Shapefile: {str(e)}")

    @staticmethod
    def save_user_layer(
        file_content: bytes,
        filename: str,
        file_type: FileType,
        name: str,
        description: str = "",
        is_public: bool = False,
        upload_ip: Optional[str] = None,
    ) -> Optional[UserLayer]:
        """Save uploaded geospatial file as a user layer."""
        try:
            # Process file based on type
            match file_type:
                case FileType.KML:
                    geom_data = GeospatialService.process_kml_file(file_content, filename)
                case FileType.KMZ:
                    geom_data = GeospatialService.process_kmz_file(file_content, filename)
                case FileType.SHP:
                    geom_data = GeospatialService.process_shp_file(file_content, filename)
                case _:
                    raise ValueError(f"Unsupported file type: {file_type}")

            # Create upload directory if it doesn't exist
            upload_dir = Path("uploads/user_layers")
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Save file to disk
            file_path = upload_dir / f"{hash(filename + str(len(file_content)))}-{filename}"
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Save to database
            with get_session() as session:
                user_layer = UserLayer(
                    name=name,
                    description=description,
                    file_type=file_type,
                    original_filename=filename,
                    file_path=str(file_path),
                    file_size=len(file_content),
                    geom_data=geom_data,
                    style_properties=GeospatialService._get_default_style(file_type),
                    is_public=is_public,
                    upload_ip=upload_ip,
                )

                session.add(user_layer)
                session.commit()
                session.refresh(user_layer)
                return user_layer

        except Exception as e:
            import logging

            logging.error(f"Error saving user layer: {e}")
            return None

    @staticmethod
    def _get_default_style(file_type: FileType) -> Dict[str, Any]:
        """Get default styling for different file types."""
        styles = {
            FileType.KML: {"color": "#3388ff", "weight": 3, "opacity": 0.8, "fillColor": "#3388ff", "fillOpacity": 0.2},
            FileType.KMZ: {"color": "#ff7800", "weight": 3, "opacity": 0.8, "fillColor": "#ff7800", "fillOpacity": 0.2},
            FileType.SHP: {"color": "#ff3333", "weight": 3, "opacity": 0.8, "fillColor": "#ff3333", "fillOpacity": 0.2},
        }
        return styles.get(file_type, styles[FileType.KML])

    @staticmethod
    def calculate_area(coordinates: List[List[float]]) -> float:
        """Calculate area of a polygon using the shoelace formula."""
        if len(coordinates) < 3:
            return 0.0

        area = 0.0
        n = len(coordinates)

        for i in range(n):
            j = (i + 1) % n
            area += coordinates[i][0] * coordinates[j][1]
            area -= coordinates[j][0] * coordinates[i][1]

        return abs(area) / 2.0

    @staticmethod
    def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates using Haversine formula."""
        import math

        lat1, lon1 = coord1
        lat2, lon2 = coord2

        # Convert latitude and longitude from degrees to radians
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        # Radius of earth in kilometers
        r = 6371

        return c * r

    @staticmethod
    def seed_default_layers() -> None:
        """Seed database with default static layers for West Lombok."""
        with get_session() as session:
            # Check if layers already exist
            existing_count = session.exec(select(StaticLayer)).first()
            if existing_count:
                return

            default_layers = [
                {
                    "name": "Sawah (Rice Fields)",
                    "layer_type": LayerType.RICE_FIELDS,
                    "description": "Peta sebaran lahan sawah di Kabupaten Lombok Barat",
                    "display_order": 1,
                    "style_properties": {
                        "color": "#4CAF50",
                        "weight": 2,
                        "opacity": 0.8,
                        "fillColor": "#81C784",
                        "fillOpacity": 0.6,
                    },
                },
                {
                    "name": "Irigasi (Irrigation)",
                    "layer_type": LayerType.IRRIGATION,
                    "description": "Jaringan sistem irigasi di Kabupaten Lombok Barat",
                    "display_order": 2,
                    "style_properties": {
                        "color": "#2196F3",
                        "weight": 3,
                        "opacity": 0.9,
                        "fillColor": "#64B5F6",
                        "fillOpacity": 0.4,
                    },
                },
                {
                    "name": "Jalan Kabupaten (Regency Roads)",
                    "layer_type": LayerType.REGENCY_ROADS,
                    "description": "Jaringan jalan kabupaten di Lombok Barat",
                    "display_order": 3,
                    "style_properties": {"color": "#FF9800", "weight": 4, "opacity": 1.0},
                },
                {
                    "name": "Batas Kabupaten (Regency Boundaries)",
                    "layer_type": LayerType.REGENCY_BOUNDARIES,
                    "description": "Batas administrasi Kabupaten Lombok Barat",
                    "display_order": 4,
                    "style_properties": {
                        "color": "#9C27B0",
                        "weight": 3,
                        "opacity": 1.0,
                        "fillColor": "#CE93D8",
                        "fillOpacity": 0.1,
                    },
                },
                {
                    "name": "Batas Desa (Village Boundaries)",
                    "layer_type": LayerType.VILLAGE_BOUNDARIES,
                    "description": "Batas administrasi desa di Kabupaten Lombok Barat",
                    "display_order": 5,
                    "style_properties": {
                        "color": "#607D8B",
                        "weight": 2,
                        "opacity": 0.8,
                        "fillColor": "#90A4AE",
                        "fillOpacity": 0.2,
                    },
                },
            ]

            for layer_data in default_layers:
                layer = StaticLayer(
                    name=layer_data["name"],
                    layer_type=layer_data["layer_type"],
                    description=layer_data["description"],
                    display_order=layer_data["display_order"],
                    style_properties=layer_data["style_properties"],
                    geom_data={
                        "type": "FeatureCollection",
                        "features": [],  # Will be populated with actual BIG data
                    },
                )
                session.add(layer)

            session.commit()
