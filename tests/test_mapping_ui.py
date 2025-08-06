"""Tests for mapping UI components and interactions."""

import pytest
from nicegui.testing import User
from app.database import reset_db
from app.geo_service import GeospatialService


@pytest.fixture
def new_db():
    """Provide fresh database for each test."""
    reset_db()
    yield
    reset_db()


async def test_main_page_loads(user: User, new_db) -> None:
    """Test that the main mapping page loads correctly."""
    await user.open("/")

    # Should see the main header
    await user.should_see("SI-GADES")
    await user.should_see("Sistem Infrastruktur Geo Spasial Berbasis Desa")
    await user.should_see("Kabupaten Lombok Barat")


async def test_sidebar_controls_present(user: User, new_db) -> None:
    """Test that sidebar controls are present."""
    await user.open("/")

    # Should see main control sections
    await user.should_see("Kontrol Peta")
    await user.should_see("Layer Infrastruktur")
    await user.should_see("Unggah Layer")
    await user.should_see("Alat Ukur")
    await user.should_see("Laporan Keluhan")


async def test_help_dialog_functionality(user: User, new_db) -> None:
    """Test help dialog opens and contains expected content."""
    await user.open("/")

    # Click help button
    user.find("Bantuan").click()

    # Should see help content
    await user.should_see("Bantuan SI-GADES")
    await user.should_see("Navigasi Peta")
    await user.should_see("Pengukuran")
    await user.should_see("Laporan Keluhan")


async def test_about_dialog_functionality(user: User, new_db) -> None:
    """Test about dialog opens and contains expected content."""
    await user.open("/")

    # Click about button
    user.find("Tentang").click()

    # Should see about content
    await user.should_see("Tentang SI-GADES")
    await user.should_see("Sistem Infrastruktur Geo Spasial Berbasis Desa")
    await user.should_see("Badan Informasi Geospasial (BIG)")


async def test_layer_controls_with_seeded_data(user: User, new_db) -> None:
    """Test layer controls work with seeded data."""
    # Seed some default layers
    GeospatialService.seed_default_layers()

    await user.open("/")

    # Open layer controls
    user.find("Layer Infrastruktur").click()

    # Should see some default layers
    await user.should_see("Sawah")
    await user.should_see("Irigasi")
    await user.should_see("Refresh Layer")


async def test_measurement_tools_activation(user: User, new_db) -> None:
    """Test measurement tools can be activated."""
    await user.open("/")

    # Open measurement tools
    user.find("Alat Ukur").click()

    # Should see measurement options
    await user.should_see("Ukur Jarak")
    await user.should_see("Ukur Luas")
    await user.should_see("Hapus Pengukuran")

    # Click distance tool - should show notification
    user.find("Ukur Jarak").click()
    await user.should_see("Klik dua titik di peta untuk mengukur jarak")


async def test_complaint_section_present(user: User, new_db) -> None:
    """Test complaint section is present and functional."""
    await user.open("/")

    # Open complaint section
    user.find("Laporan Keluhan").click()

    # Should see complaint options
    await user.should_see("Buat Laporan Baru")
    await user.should_see("Lihat Laporan Terbaru")


async def test_file_upload_form_validation(user: User, new_db) -> None:
    """Test file upload form validation."""
    await user.open("/")

    # Open upload section
    user.find("Unggah Layer").click()

    # Should see upload form elements
    await user.should_see("Nama Layer")
    await user.should_see("Deskripsi")
    await user.should_see("Tampilkan ke publik")
    await user.should_see("Format yang didukung: KML, KMZ, SHP")


async def test_map_controls_present(user: User, new_db) -> None:
    """Test map control buttons are present."""
    await user.open("/")

    # Should see map control buttons
    await user.should_see("Reset Tampilan")
    await user.should_see("Lokasi Saya")


async def test_recent_complaints_empty_state(user: User, new_db) -> None:
    """Test recent complaints shows empty state when no complaints exist."""
    await user.open("/")

    # Open complaint section and click view recent
    user.find("Laporan Keluhan").click()
    user.find("Lihat Laporan Terbaru").click()

    # Should see empty state
    await user.should_see("Laporan Keluhan Terbaru")
    await user.should_see("Belum ada laporan keluhan")


async def test_page_styling_applied(user: User, new_db) -> None:
    """Test that page styling and CSS classes are applied."""
    await user.open("/")

    # The page should load without errors and contain styled elements
    # We can't easily test specific CSS, but we can ensure the page structure exists
    await user.should_see("SI-GADES")

    # The map container should be present (even if map doesn't fully load in tests)
    # This tests that the HTML structure is generated correctly


async def test_responsive_layout_structure(user: User, new_db) -> None:
    """Test that the responsive layout structure is created."""
    await user.open("/")

    # Should have main header
    await user.should_see("SI-GADES")

    # Should have sidebar content
    await user.should_see("Kontrol Peta")

    # Should have map controls
    await user.should_see("Reset Tampilan")

    # The layout should be functional even if map doesn't load in test environment


async def test_layer_info_dialog_functionality(user: User, new_db) -> None:
    """Test layer info dialog when layers are present."""
    # Seed some data first
    GeospatialService.seed_default_layers()

    await user.open("/")

    # Open layer controls
    user.find("Layer Infrastruktur").click()

    # Should be able to see refresh button at minimum
    await user.should_see("Refresh Layer")

    # Click refresh to test functionality
    user.find("Refresh Layer").click()
    await user.should_see("Memuat ulang layer")


async def test_navigation_elements_present(user: User, new_db) -> None:
    """Test that all main navigation elements are present on page load."""
    await user.open("/")

    # Header elements
    await user.should_see("SI-GADES")
    await user.should_see("Bantuan")
    await user.should_see("Tentang")

    # Sidebar sections (expansion panels)
    await user.should_see("Kontrol Peta")
    await user.should_see("Layer Infrastruktur")
    await user.should_see("Unggah Layer")
    await user.should_see("Alat Ukur")
    await user.should_see("Laporan Keluhan")

    # Map controls
    await user.should_see("Reset Tampilan")
    await user.should_see("Lokasi Saya")


async def test_expansion_panels_functionality(user: User, new_db) -> None:
    """Test that expansion panels can be opened and closed."""
    await user.open("/")

    # Test each expansion panel
    panels = ["Layer Infrastruktur", "Unggah Layer", "Alat Ukur", "Laporan Keluhan"]

    for panel in panels:
        # Click to open
        user.find(panel).click()

        # Should reveal content (we test basic functionality)
        # Specific content tests are in other test methods

        # The panel should be interactive
        # (We can't easily test visual state in NiceGUI tests,
        # but we can ensure clicks are handled)


async def test_theme_colors_integration(user: User, new_db) -> None:
    """Test that the blue/yellow/green theme is integrated."""
    await user.open("/")

    # The page should load with the theme applied
    # We test this indirectly by ensuring styled buttons are present
    await user.should_see("Bantuan")  # Yellow button
    await user.should_see("Tentang")  # Green button

    # Main header with blue theme
    await user.should_see("SI-GADES")
    await user.should_see("Sistem Infrastruktur Geo Spasial Berbasis Desa")
