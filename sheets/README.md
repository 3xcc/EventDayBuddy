"""
Sheets Package
==============

This package provides a modular interface for working with Google Sheets
in EventDayBuddy (EDB). It replaces the old monolithic `manager.py` with
a clean separation of concerns.

Modules
-------

- client.py
    Handles Google Sheets API client setup and authentication.
    Exposes `service` and `SPREADSHEET_ID`.

- constants.py
    Centralized headers, tab names, and row limits.
    Defines `MASTER_HEADERS`, `EVENT_HEADERS`, `MASTER_TAB`, etc.

- validators.py
    Validation utilities for sheet alignment and data integrity.
    - `validate_sheet_alignment(sheet_name, expected_columns)`

- booking_io.py
    Low-level booking operations:
    - `create_event_tab(event_name)`
    - `append_to_master(event_name, booking_row)`
    - `append_to_event(event_name, booking_row)`
    - `update_booking_row(event_name, ticket_ref, updates)`
    - `update_booking_in_sheets(event_name, booking)`
    - `update_booking_photo(event_name, ticket_ref, photo_url)`

- queries.py
    Read/query operations:
    - `get_manifest_rows(boat_number, event_name=None)`

- exports.py
    Export operations:
    - `export_manifest_pdf(boat_number, event_name=None)`

- manager.py
    High-level orchestrator and public API.
    Provides clean entry points for the rest of the app:
    - `ensure_event_tab(event_name)`
    - `add_booking(event_name, booking_row)`
    - `update_booking(event_name, booking)`
    - `update_photo(event_name, ticket_ref, photo_url)`
    - `manifest_for_boat(boat_number, event_name=None)`
    - `export_manifest(boat_number, event_name=None)`

Usage
-----

Import only from `sheets.manager` in the rest of the codebase:

    from sheets.manager import (
        ensure_event_tab,
        add_booking,
        update_booking,
        manifest_for_boat,
        export_manifest,
    )

This keeps the rest of the system decoupled from internal details,
so we can evolve the internals without breaking callers.

Design Notes
------------

- `manager.py` is intentionally thin: it orchestrates, not implements.
- Each submodule has a single responsibility.
- Validators run before writes to catch misaligned headers early.
- Exports are isolated so future formats (CSV, Excel) can be added easily.
"""