from app.database import create_tables
from app.geo_service import GeospatialService
from app import mapping


def startup() -> None:
    # Initialize database and seed default data
    create_tables()
    GeospatialService.seed_default_layers()

    # Create mapping application routes
    mapping.create()
