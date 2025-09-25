def format_import_summary(result: dict) -> str:
    """
    Format a human-friendly summary of the bulk import result.
    Expected result dict:
    {
        "inserted": int,
        "skipped": int,
        "errors": list[str],
        "missing_photos": list[str]
    }
    """
    inserted = result.get("inserted", 0)
    skipped = result.get("skipped", 0)
    errors = result.get("errors", [])
    missing_photos = result.get("missing_photos", [])

    lines = []
    lines.append("📥 Bulk Import Complete")
    lines.append(f"✅ {inserted} bookings imported")

    if skipped:
        lines.append(f"⚠️ {skipped} rows skipped")
    if errors:
        # Show only first few errors inline, rest summarized
        preview = errors[:3]
        lines.append("❌ Errors:")
        for err in preview:
            lines.append(f"   • {err}")
        if len(errors) > 3:
            lines.append(f"   … and {len(errors) - 3} more")

    if missing_photos:
        count = len(missing_photos)
        preview = missing_photos[:5]
        lines.append(f"🪪 {count} bookings missing photos")
        lines.append("   Use /attachphoto <ID> to upload")
        # Show first few IDs inline
        lines.append("   Missing IDs: " + ", ".join(preview))
        if count > 5:
            lines.append(f"   … and {count - 5} more")

    return "\n".join(lines)