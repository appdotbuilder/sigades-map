"""Service layer for managing public complaints with geolocation and photos."""

from pathlib import Path
from typing import Optional, List
from decimal import Decimal

from sqlmodel import select, col
from app.database import get_session
from app.models import (
    Complaint,
    ComplaintPhoto,
    ComplaintCreate,
    ComplaintResponse,
    ComplaintPhotoResponse,
    ComplaintStatus,
)


class ComplaintService:
    """Service for managing public complaints."""

    UPLOAD_DIR = Path("uploads/complaint_photos")
    ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB

    @classmethod
    def setup_upload_dir(cls) -> None:
        """Ensure upload directory exists."""
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_complaint(complaint_data: ComplaintCreate, submit_ip: Optional[str] = None) -> Optional[Complaint]:
        """Create a new complaint with geolocation."""
        try:
            with get_session() as session:
                complaint = Complaint(
                    title=complaint_data.title,
                    description=complaint_data.description,
                    latitude=complaint_data.latitude,
                    longitude=complaint_data.longitude,
                    location_description=complaint_data.location_description,
                    submitter_name=complaint_data.submitter_name,
                    submitter_email=complaint_data.submitter_email,
                    submitter_phone=complaint_data.submitter_phone,
                    submit_ip=submit_ip,
                    status=ComplaintStatus.SUBMITTED,
                )

                session.add(complaint)
                session.commit()
                session.refresh(complaint)
                return complaint

        except Exception as e:
            import logging

            logging.error(f"Error creating complaint: {e}")
            return None

    @staticmethod
    def add_photo_to_complaint(
        complaint_id: int, file_content: bytes, filename: str, mime_type: str, caption: str = "", display_order: int = 0
    ) -> Optional[ComplaintPhoto]:
        """Add a photo to an existing complaint."""
        try:
            # Validate file type and size
            if mime_type not in ComplaintService.ALLOWED_PHOTO_TYPES:
                raise ValueError(f"Unsupported file type: {mime_type}")

            if len(file_content) > ComplaintService.MAX_PHOTO_SIZE:
                raise ValueError("File size exceeds maximum limit (5MB)")

            # Ensure upload directory exists
            ComplaintService.setup_upload_dir()

            # Generate unique filename
            file_extension = filename.split(".")[-1] if "." in filename else "jpg"
            safe_filename = f"complaint_{complaint_id}_{hash(filename + str(len(file_content)))}.{file_extension}"
            file_path = ComplaintService.UPLOAD_DIR / safe_filename

            # Save file to disk
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Save to database
            with get_session() as session:
                photo = ComplaintPhoto(
                    complaint_id=complaint_id,
                    filename=filename,
                    file_path=str(file_path),
                    file_size=len(file_content),
                    mime_type=mime_type,
                    caption=caption,
                    display_order=display_order,
                )

                session.add(photo)
                session.commit()
                session.refresh(photo)
                return photo

        except Exception as e:
            import logging

            logging.error(f"Error adding photo to complaint: {e}")
            return None

    @staticmethod
    def get_complaint(complaint_id: int) -> Optional[ComplaintResponse]:
        """Get a complaint by ID with all its photos."""
        with get_session() as session:
            complaint = session.get(Complaint, complaint_id)
            if not complaint:
                return None

            # Get photos
            photos = session.exec(
                select(ComplaintPhoto)
                .where(ComplaintPhoto.complaint_id == complaint_id)
                .order_by(col(ComplaintPhoto.display_order), col(ComplaintPhoto.created_at))
            ).all()

            photo_responses = [
                ComplaintPhotoResponse(
                    id=photo.id or 0,
                    filename=photo.filename,
                    file_path=photo.file_path,
                    mime_type=photo.mime_type,
                    caption=photo.caption,
                    display_order=photo.display_order,
                )
                for photo in photos
            ]

            return ComplaintResponse(
                id=complaint.id or 0,
                title=complaint.title,
                description=complaint.description,
                latitude=complaint.latitude,
                longitude=complaint.longitude,
                location_description=complaint.location_description,
                submitter_name=complaint.submitter_name,
                status=complaint.status,
                created_at=complaint.created_at.isoformat(),
                photos=photo_responses,
            )

    @staticmethod
    def get_recent_complaints(limit: int = 50) -> List[ComplaintResponse]:
        """Get recent complaints for display."""
        with get_session() as session:
            complaints = session.exec(select(Complaint).order_by(col(Complaint.created_at).desc()).limit(limit)).all()

            responses = []
            for complaint in complaints:
                # Get photos for each complaint
                photos = session.exec(
                    select(ComplaintPhoto)
                    .where(ComplaintPhoto.complaint_id == complaint.id)
                    .order_by(col(ComplaintPhoto.display_order))
                ).all()

                photo_responses = [
                    ComplaintPhotoResponse(
                        id=photo.id or 0,
                        filename=photo.filename,
                        file_path=photo.file_path,
                        mime_type=photo.mime_type,
                        caption=photo.caption,
                        display_order=photo.display_order,
                    )
                    for photo in photos
                ]

                responses.append(
                    ComplaintResponse(
                        id=complaint.id or 0,
                        title=complaint.title,
                        description=complaint.description,
                        latitude=complaint.latitude,
                        longitude=complaint.longitude,
                        location_description=complaint.location_description,
                        submitter_name=complaint.submitter_name,
                        status=complaint.status,
                        created_at=complaint.created_at.isoformat(),
                        photos=photo_responses,
                    )
                )

            return responses

    @staticmethod
    def mark_redirected(complaint_id: int, platform: str) -> bool:
        """Mark complaint as redirected to external platform."""
        try:
            with get_session() as session:
                complaint = session.get(Complaint, complaint_id)
                if not complaint:
                    return False

                if platform.lower() == "facebook":
                    complaint.facebook_redirected = True
                elif platform.lower() == "lapor":
                    complaint.lapor_redirected = True

                # Update status if redirected to both platforms
                if complaint.facebook_redirected and complaint.lapor_redirected:
                    complaint.status = ComplaintStatus.COMPLETED
                else:
                    complaint.status = ComplaintStatus.REDIRECTED

                session.add(complaint)
                session.commit()
                return True

        except Exception as e:
            import logging

            logging.error(f"Error marking complaint as redirected: {e}")
            return False

    @staticmethod
    def get_complaints_in_area(south: float, west: float, north: float, east: float) -> List[ComplaintResponse]:
        """Get complaints within a geographic bounding box."""
        with get_session() as session:
            complaints = session.exec(
                select(Complaint)
                .where(
                    Complaint.latitude >= Decimal(str(south)),
                    Complaint.latitude <= Decimal(str(north)),
                    Complaint.longitude >= Decimal(str(west)),
                    Complaint.longitude <= Decimal(str(east)),
                )
                .order_by(col(Complaint.created_at).desc())
            ).all()

            responses = []
            for complaint in complaints:
                # Get photos for each complaint
                photos = session.exec(
                    select(ComplaintPhoto)
                    .where(ComplaintPhoto.complaint_id == complaint.id)
                    .order_by(col(ComplaintPhoto.display_order))
                ).all()

                photo_responses = [
                    ComplaintPhotoResponse(
                        id=photo.id or 0,
                        filename=photo.filename,
                        file_path=photo.file_path,
                        mime_type=photo.mime_type,
                        caption=photo.caption,
                        display_order=photo.display_order,
                    )
                    for photo in photos
                ]

                responses.append(
                    ComplaintResponse(
                        id=complaint.id or 0,
                        title=complaint.title,
                        description=complaint.description,
                        latitude=complaint.latitude,
                        longitude=complaint.longitude,
                        location_description=complaint.location_description,
                        submitter_name=complaint.submitter_name,
                        status=complaint.status,
                        created_at=complaint.created_at.isoformat(),
                        photos=photo_responses,
                    )
                )

            return responses
