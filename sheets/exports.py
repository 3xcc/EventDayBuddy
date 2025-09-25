from config.logger import logger, log_and_raise

def export_manifest_pdf(boat_number: str, event_name: str = None):
    """
    Generate and upload a manifest PDF to Supabase.
    Returns the Supabase path (e.g. manifests/<event>/boat_<n>.pdf).
    """
    try:
        from utils.supabase_storage import upload_manifest
        from utils.pdf_generator import generate_manifest_pdf

        pdf_bytes = generate_manifest_pdf(boat_number, event_name=event_name)
        if not pdf_bytes:
            raise Exception("No PDF bytes generated")

        path = upload_manifest(pdf_bytes, event_name or "General", boat_number)
        logger.info(f"[Sheets] Manifest PDF uploaded to Supabase for Boat {boat_number}: {path}")
        return path
    except Exception as e:
        log_and_raise("Sheets", f"exporting manifest PDF for boat {boat_number}", e)