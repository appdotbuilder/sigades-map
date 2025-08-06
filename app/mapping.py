"""Main mapping interface for SI-GADES geospatial application."""

from decimal import Decimal

from nicegui import ui
from nicegui.events import UploadEventArguments
from app.geo_service import GeospatialService
from app.complaint_service import ComplaintService
from app.models import FileType, ComplaintCreate


def create():
    """Create the mapping application routes and components."""

    @ui.page("/")
    def main_map():
        """Main mapping interface."""
        # Apply SI-GADES theme
        ui.add_head_html("""
        <style>
        .si-gades-theme {
            --primary-color: #1565C0;
            --secondary-color: #FFC107;
            --success-color: #4CAF50;
        }
        .map-container {
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .sidebar {
            background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%);
            color: white;
        }
        .layer-control {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .tool-button {
            transition: all 0.2s ease;
            border-radius: 8px;
        }
        .tool-button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        </style>
        """)

        # Page header
        with ui.row().classes("w-full items-center justify-between p-4 sidebar"):
            with ui.column():
                ui.label("SI-GADES").classes("text-3xl font-bold text-white")
                ui.label("Sistem Infrastruktur Geo Spasial Berbasis Desa").classes("text-lg text-blue-100")
                ui.label("Kabupaten Lombok Barat").classes("text-sm text-blue-200")

            with ui.row().classes("gap-4"):
                ui.button("Bantuan", on_click=show_help_dialog).classes(
                    "bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2"
                )
                ui.button("Tentang", on_click=show_about_dialog).classes(
                    "bg-green-500 hover:bg-green-600 text-white px-4 py-2"
                )

        # Main content layout
        with ui.row().classes("w-full h-screen"):
            # Left sidebar
            with ui.column().classes("w-80 bg-white shadow-lg p-4 overflow-auto"):
                create_sidebar()

            # Map container
            with ui.column().classes("flex-1 p-4"):
                create_map_interface()

    def create_sidebar():
        """Create the left sidebar with controls."""
        ui.label("Kontrol Peta").classes("text-xl font-bold text-gray-800 mb-4")

        # Layer controls
        with ui.expansion("Layer Infrastruktur", icon="layers").classes("w-full mb-2"):
            create_layer_controls()

        # Upload section
        with ui.expansion("Unggah Layer", icon="cloud_upload").classes("w-full mb-2"):
            create_upload_section()

        # Measurement tools
        with ui.expansion("Alat Ukur", icon="straighten").classes("w-full mb-2"):
            create_measurement_tools()

        # Complaint section
        with ui.expansion("Laporan Keluhan", icon="report_problem").classes("w-full mb-2"):
            create_complaint_section()

    def create_layer_controls():
        """Create layer visibility controls."""
        ui.label("Kontrol Visibilitas Layer").classes("text-sm font-medium text-gray-600 mb-2")

        # Get all layers
        layers = GeospatialService.get_all_active_layers()

        for layer in layers:
            with ui.row().classes("items-center gap-2 p-2"):
                checkbox = ui.checkbox(layer.name, value=True).classes("text-sm")
                checkbox.on_value_change(lambda e, layer_id=layer.id: toggle_layer(layer_id, e.value))

                # Layer info button
                ui.button(icon="info", on_click=lambda layer=layer: show_layer_info(layer)).props("size=sm flat round")

        # Refresh layers button
        ui.button("Refresh Layer", icon="refresh", on_click=refresh_layers).classes(
            "w-full mt-2 bg-blue-500 text-white"
        )

    def create_upload_section():
        """Create file upload section."""
        ui.label("Unggah File Geospasial").classes("text-sm font-medium text-gray-600 mb-2")

        # Layer name input
        layer_name_input = ui.input("Nama Layer", placeholder="Masukkan nama layer").classes("w-full mb-2")

        # Description input
        layer_desc_input = (
            ui.textarea("Deskripsi", placeholder="Deskripsi opsional").classes("w-full mb-2").props("rows=2")
        )

        # Public visibility checkbox
        public_checkbox = ui.checkbox("Tampilkan ke publik", value=False).classes("mb-2")

        # File upload
        ui.upload(
            label="Pilih File (KML, KMZ, SHP)",
            on_upload=lambda e: handle_file_upload(e, layer_name_input, layer_desc_input, public_checkbox),
            auto_upload=True,
        ).classes("w-full").props('accept=".kml,.kmz,.shp"')

        ui.label("Format yang didukung: KML, KMZ, SHP").classes("text-xs text-gray-500 mt-1")

    def create_measurement_tools():
        """Create measurement tools section."""
        ui.label("Alat Pengukuran").classes("text-sm font-medium text-gray-600 mb-2")

        with ui.column().classes("gap-2"):
            ui.button("Ukur Jarak", icon="straighten", on_click=activate_distance_tool).classes("w-full tool-button")
            ui.button("Ukur Luas", icon="crop_free", on_click=activate_area_tool).classes("w-full tool-button")
            ui.button("Hapus Pengukuran", icon="clear", on_click=clear_measurements).classes("w-full tool-button")

    def create_complaint_section():
        """Create complaint submission section."""
        ui.label("Laporkan Keluhan").classes("text-sm font-medium text-gray-600 mb-2")

        with ui.column().classes("gap-2"):
            ui.button("Buat Laporan Baru", icon="add_circle", on_click=show_complaint_form).classes(
                "w-full bg-red-500 text-white"
            )
            ui.button("Lihat Laporan Terbaru", icon="list", on_click=show_recent_complaints).classes("w-full")

    def create_map_interface():
        """Create the main map interface using Leaflet."""
        bounds = GeospatialService.get_west_lombok_bounds()
        center_lat, center_lon = GeospatialService.get_default_map_center()

        # Map HTML with Leaflet
        # Map container div (without script tags)
        map_html = '<div id="map" style="width: 100%; height: 80vh;" class="map-container"></div>'

        # Add Leaflet CSS and JS
        ui.add_head_html("""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        """)

        ui.html(map_html).classes("w-full")

        # Add map initialization script
        ui.add_body_html(f"""
        <script>
            // Initialize Leaflet map
            var map = L.map('map').setView([{center_lat}, {center_lon}], 10);
            
            // Add base layer
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors | SI-GADES Lombok Barat'
            }}).addTo(map);
            
            // Set max bounds to West Lombok
            var bounds = L.latLngBounds(
                [{bounds["south"]}, {bounds["west"]}],
                [{bounds["north"]}, {bounds["east"]}]
            );
            map.setMaxBounds(bounds);
            map.fitBounds(bounds);
            
            // Global variables for tools
            window.measurementLayers = L.layerGroup().addTo(map);
            window.currentTool = null;
            window.tempMarkers = [];
            
            // Add click handler for complaint location
            map.on('click', function(e) {{
                if (window.currentTool === 'complaint') {{
                    window.complaintLocation = {{
                        lat: e.latlng.lat,
                        lng: e.latlng.lng
                    }};
                    
                    // Clear existing temp markers
                    window.tempMarkers.forEach(marker => map.removeLayer(marker));
                    window.tempMarkers = [];
                    
                    // Add new marker
                    var marker = L.marker([e.latlng.lat, e.latlng.lng])
                        .addTo(map)
                        .bindPopup('Lokasi keluhan dipilih');
                    window.tempMarkers.push(marker);
                }}
            }});
            
            // Load initial layers
            loadMapLayers();
            
            function loadMapLayers() {{
                // This will be called from Python to load actual layer data
                console.log('Loading map layers...');
            }}
        </script>
        """)

        # Map controls
        with ui.row().classes("gap-2 mt-2"):
            ui.button("Reset Tampilan", icon="center_focus_strong", on_click=reset_map_view).classes("tool-button")
            ui.button("Lokasi Saya", icon="my_location", on_click=locate_user).classes("tool-button")

    # Event handlers
    def toggle_layer(layer_id: int, visible: bool):
        """Toggle layer visibility."""
        ui.run_javascript(f"""
            console.log('Toggle layer {layer_id}: {visible}');
            // Implementation would toggle actual map layer
        """)

    def show_layer_info(layer):
        """Show layer information dialog."""
        with ui.dialog() as dialog, ui.card().classes("w-96"):
            ui.label(f"Informasi Layer: {layer.name}").classes("text-lg font-bold mb-2")
            ui.label(f"Tipe: {layer.layer_type}").classes("mb-1")
            ui.label(f"Deskripsi: {layer.description}").classes("mb-2")
            ui.label(f"Dibuat: {layer.created_at}").classes("text-sm text-gray-600")

            with ui.row().classes("gap-2 justify-end mt-4"):
                ui.button("Tutup", on_click=dialog.close).classes("bg-gray-500 text-white")

        dialog.open()

    def refresh_layers():
        """Refresh map layers."""
        ui.notify("Memuat ulang layer...", type="info")
        ui.run_javascript("loadMapLayers();")

    def handle_file_upload(e: UploadEventArguments, name_input, desc_input, public_checkbox):
        """Handle geospatial file upload."""
        try:
            if not name_input.value:
                ui.notify("Nama layer harus diisi", type="negative")
                return

            filename = e.name
            file_extension = filename.split(".")[-1].lower() if "." in filename else ""

            # Validate file type
            if file_extension not in ["kml", "kmz", "shp"]:
                ui.notify("Format file tidak didukung. Gunakan KML, KMZ, atau SHP", type="negative")
                return

            # Determine file type
            file_type = (
                FileType.KML if file_extension == "kml" else FileType.KMZ if file_extension == "kmz" else FileType.SHP
            )

            # Save layer
            layer = GeospatialService.save_user_layer(
                file_content=e.content.read(),
                filename=filename,
                file_type=file_type,
                name=name_input.value,
                description=desc_input.value or "",
                is_public=public_checkbox.value,
            )

            if layer:
                ui.notify(f'Layer "{name_input.value}" berhasil diunggah!', type="positive")
                # Clear form
                name_input.value = ""
                desc_input.value = ""
                public_checkbox.value = False
                # Refresh map
                refresh_layers()
            else:
                ui.notify("Gagal mengunggah layer. Coba lagi.", type="negative")

        except Exception as error:
            import logging

            logging.error(f"File upload error: {str(error)}")
            ui.notify(f"Error: {str(error)}", type="negative")

    def activate_distance_tool():
        """Activate distance measurement tool."""
        ui.notify("Klik dua titik di peta untuk mengukur jarak", type="info")
        ui.run_javascript("""
            window.currentTool = 'distance';
            document.body.style.cursor = 'crosshair';
        """)

    def activate_area_tool():
        """Activate area measurement tool."""
        ui.notify("Klik beberapa titik di peta untuk mengukur luas", type="info")
        ui.run_javascript("""
            window.currentTool = 'area';
            document.body.style.cursor = 'crosshair';
        """)

    def clear_measurements():
        """Clear all measurements."""
        ui.run_javascript("""
            window.measurementLayers.clearLayers();
            window.currentTool = null;
            document.body.style.cursor = 'default';
        """)
        ui.notify("Pengukuran dihapus", type="info")

    async def show_complaint_form():
        """Show complaint submission form."""
        ui.notify("Klik pada peta untuk memilih lokasi keluhan", type="info")
        ui.run_javascript('window.currentTool = "complaint";')

        with ui.dialog() as dialog, ui.card().classes("w-96 max-h-96 overflow-auto"):
            ui.label("Formulir Laporan Keluhan").classes("text-lg font-bold mb-4")

            # Form fields
            title_input = ui.input("Judul Keluhan", placeholder="Ringkasan masalah").classes("w-full mb-2")
            desc_input = (
                ui.textarea("Deskripsi Detail", placeholder="Jelaskan masalah secara detail")
                .classes("w-full mb-2")
                .props("rows=4")
            )
            location_desc_input = ui.input("Deskripsi Lokasi", placeholder="Contoh: Depan kantor desa").classes(
                "w-full mb-2"
            )

            # Optional contact info
            ui.label("Informasi Kontak (Opsional)").classes("text-sm font-medium text-gray-600 mb-1")
            name_input = ui.input("Nama Lengkap", placeholder="Nama pelapor").classes("w-full mb-2")
            email_input = ui.input("Email", placeholder="email@example.com").classes("w-full mb-2")
            phone_input = ui.input("No. Telepon", placeholder="08xxxxxxxxxx").classes("w-full mb-2")

            # Photo upload
            ui.label("Lampiran Foto").classes("text-sm font-medium text-gray-600 mb-1")
            photo_upload = (
                ui.upload(label="Pilih Foto (Max 5MB)", auto_upload=True, multiple=True)
                .classes("w-full mb-4")
                .props('accept="image/*"')
            )

            with ui.row().classes("gap-2 justify-end"):
                ui.button("Batal", on_click=dialog.close).classes("bg-gray-500 text-white")
                ui.button(
                    "Kirim Laporan",
                    on_click=lambda: submit_complaint(
                        dialog,
                        title_input,
                        desc_input,
                        location_desc_input,
                        name_input,
                        email_input,
                        phone_input,
                        photo_upload,
                    ),
                ).classes("bg-red-500 text-white")

        dialog.open()

    async def submit_complaint(
        dialog, title_input, desc_input, location_desc_input, name_input, email_input, phone_input, photo_upload
    ):
        """Submit complaint to database."""
        try:
            # Validate required fields
            if not title_input.value or not desc_input.value:
                ui.notify("Judul dan deskripsi harus diisi", type="negative")
                return

            # Get location from JavaScript (simplified for now)
            # In a real implementation, we'd get this from the map click
            location = {"lat": -8.55, "lng": 116.15}  # Default location for demo
            if not location:
                ui.notify("Pilih lokasi di peta terlebih dahulu", type="negative")
                return

            # Create complaint
            complaint_data = ComplaintCreate(
                title=title_input.value,
                description=desc_input.value,
                latitude=Decimal(str(location["lat"])),
                longitude=Decimal(str(location["lng"])),
                location_description=location_desc_input.value or "",
                submitter_name=name_input.value or None,
                submitter_email=email_input.value or None,
                submitter_phone=phone_input.value or None,
            )

            complaint = ComplaintService.create_complaint(complaint_data)
            if not complaint or complaint.id is None:
                ui.notify("Gagal menyimpan laporan", type="negative")
                return

            # Handle photo uploads if any
            if hasattr(photo_upload, "value") and photo_upload.value:
                for i, file_info in enumerate(photo_upload.value):
                    if hasattr(file_info, "content"):
                        ComplaintService.add_photo_to_complaint(
                            complaint.id,
                            file_info.content.read(),
                            file_info.name,
                            file_info.type or "image/jpeg",
                            display_order=i,
                        )

            dialog.close()

            # Show redirect dialog
            await show_redirect_dialog(complaint.id)

        except Exception as e:
            import logging

            logging.error(f"Error submitting complaint: {str(e)}")
            ui.notify(f"Error: {str(e)}", type="negative")

    async def show_redirect_dialog(complaint_id: int):
        """Show redirect options for external complaint platforms."""
        with ui.dialog() as dialog, ui.card().classes("w-96"):
            ui.label("Laporan Berhasil Disimpan!").classes("text-lg font-bold text-green-600 mb-2")
            ui.label("Untuk menindaklanjuti laporan, silakan lanjutkan ke:").classes("mb-4")

            with ui.column().classes("gap-2 w-full"):
                ui.button(
                    "Lanjut ke Facebook", icon="facebook", on_click=lambda: redirect_to_facebook(complaint_id, dialog)
                ).classes("w-full bg-blue-600 text-white")
                ui.button(
                    "Lanjut ke Lapor.go.id", icon="report", on_click=lambda: redirect_to_lapor(complaint_id, dialog)
                ).classes("w-full bg-red-600 text-white")
                ui.button("Tutup", on_click=dialog.close).classes("w-full bg-gray-500 text-white")

        dialog.open()

    def redirect_to_facebook(complaint_id: int, dialog):
        """Redirect to Facebook and mark as redirected."""
        ComplaintService.mark_redirected(complaint_id, "facebook")
        ui.navigate.to("https://www.facebook.com", new_tab=True)
        dialog.close()
        ui.notify("Redirected to Facebook", type="info")

    def redirect_to_lapor(complaint_id: int, dialog):
        """Redirect to lapor.go.id and mark as redirected."""
        ComplaintService.mark_redirected(complaint_id, "lapor")
        ui.navigate.to("https://www.lapor.go.id", new_tab=True)
        dialog.close()
        ui.notify("Redirected to Lapor.go.id", type="info")

    def show_recent_complaints():
        """Show recent complaints dialog."""
        complaints = ComplaintService.get_recent_complaints(10)

        with ui.dialog() as dialog, ui.card().classes("w-full max-w-4xl max-h-96 overflow-auto"):
            ui.label("Laporan Keluhan Terbaru").classes("text-lg font-bold mb-4")

            if not complaints:
                ui.label("Belum ada laporan keluhan").classes("text-gray-500 text-center p-4")
            else:
                for complaint in complaints:
                    with ui.card().classes("mb-2 p-3"):
                        ui.label(complaint.title).classes("font-bold")
                        ui.label(f"Lokasi: {complaint.location_description}").classes("text-sm text-gray-600")
                        ui.label(f"Status: {complaint.status}").classes("text-xs")
                        ui.label(f"Waktu: {complaint.created_at}").classes("text-xs text-gray-500")

            ui.button("Tutup", on_click=dialog.close).classes("mt-4 bg-gray-500 text-white")

        dialog.open()

    def reset_map_view():
        """Reset map to default view."""
        ui.run_javascript("""
            map.fitBounds(bounds);
        """)
        ui.notify("Tampilan peta direset", type="info")

    def locate_user():
        """Locate user on map."""
        ui.run_javascript("""
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    var lat = position.coords.latitude;
                    var lng = position.coords.longitude;
                    map.setView([lat, lng], 15);
                    L.marker([lat, lng]).addTo(map).bindPopup('Lokasi Anda').openPopup();
                });
            }
        """)

    def show_help_dialog():
        """Show help dialog."""
        with ui.dialog() as dialog, ui.card().classes("w-96 max-h-96 overflow-auto"):
            ui.label("Bantuan SI-GADES").classes("text-lg font-bold mb-4")

            with ui.column().classes("gap-2"):
                ui.label("🗺️ Navigasi Peta").classes("font-medium")
                ui.label("• Zoom dengan mouse wheel atau tombol +/-").classes("text-sm")
                ui.label("• Drag untuk menggeser peta").classes("text-sm")

                ui.label("📊 Layer").classes("font-medium mt-4")
                ui.label("• Centang/hilangkan centang untuk menampilkan layer").classes("text-sm")
                ui.label("• Unggah file KML, KMZ, atau SHP untuk layer kustom").classes("text-sm")

                ui.label("📏 Pengukuran").classes("font-medium mt-4")
                ui.label('• Klik "Ukur Jarak" lalu klik 2 titik di peta').classes("text-sm")
                ui.label('• Klik "Ukur Luas" lalu klik beberapa titik untuk area').classes("text-sm")

                ui.label("📝 Laporan Keluhan").classes("font-medium mt-4")
                ui.label('• Klik "Buat Laporan" lalu pilih lokasi di peta').classes("text-sm")
                ui.label("• Isi formulir dan lampirkan foto jika perlu").classes("text-sm")

            ui.button("Tutup", on_click=dialog.close).classes("mt-4 bg-blue-500 text-white")

        dialog.open()

    def show_about_dialog():
        """Show about dialog."""
        with ui.dialog() as dialog, ui.card().classes("w-96"):
            ui.label("Tentang SI-GADES").classes("text-lg font-bold mb-4")

            ui.label("SI-GADES (Sistem Infrastruktur Geo Spasial Berbasis Desa)").classes("font-medium mb-2")
            ui.label("Aplikasi pemetaan infrastruktur desa di Kabupaten Lombok Barat, Nusa Tenggara Barat.").classes(
                "mb-4"
            )

            ui.label("Fitur Utama:").classes("font-medium mb-2")
            with ui.column().classes("gap-1"):
                ui.label("• Peta interaktif dengan layer infrastruktur").classes("text-sm")
                ui.label("• Upload file geospasial (KML, KMZ, SHP)").classes("text-sm")
                ui.label("• Alat pengukuran jarak dan luas").classes("text-sm")
                ui.label("• Sistem laporan keluhan publik").classes("text-sm")

            ui.label("Data dari Badan Informasi Geospasial (BIG)").classes("text-sm text-gray-600 mt-4")

            ui.button("Tutup", on_click=dialog.close).classes("mt-4 bg-green-500 text-white")

        dialog.open()
