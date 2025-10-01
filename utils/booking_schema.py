from datetime import datetime
from decimal import Decimal

# Master tab headers (full schema, includes Event + audit fields)
MASTER_HEADERS = [
    "No",
    "Event",
    "TicketRef",
    "Name",
    "IDNumber",
    "Phone",
    "MaleDep",
    "ResortDep",
    "ArrivalTime",
    "DepartureTime",
    "PaidAmount",
    "TransferRef",
    "TicketType",
    "ArrivalBoatBoarded",
    "DepartureBoatBoarded",
    "CheckinTime",
    "Status",
    "ID Doc URL",
    "GroupID",
    "CreatedAt",
    "UpdatedAt",
]

# Event tab headers (slim schema, no Event column, slightly different labels)
EVENT_HEADERS = [
    "No",
    "T. Reference",
    "Name",
    "ID",
    "Number",
    "Male' Dep",
    "Resort Dep",
    "Paid Amount",
    "Transfer slip Ref",
    "Ticket Type",
    "Check in Time",
    "Status",
    "ID Doc URL",
    "ArrivalTime",
    "DepartureTime",
    "ArrivalBoatBoarded",
    "DepartureBoatBoarded",
]


def _format_amount(value) -> str:
    """Format paid amount safely as string with 2 decimals if numeric."""
    if value is None or value == "":
        return ""
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def build_master_row(booking: dict, event_name: str) -> list:
    """
    Build a row aligned with MASTER_HEADERS from a booking dict.
    Preserves CreatedAt if provided, always refreshes UpdatedAt.
    """
    now = datetime.now().isoformat()
    created_at = booking.get("created_at") or now
    updated_at = now

    return [
        "",  # No (auto in Sheets)
        event_name,
        booking.get("ticket_ref") or "",
        booking.get("name") or "",
        booking.get("id_number") or "",
        booking.get("phone") or "",
        booking.get("male_dep") or "",
        booking.get("resort_dep") or "",
        booking.get("arrival_time") or "",
        booking.get("departure_time") or "",
        _format_amount(booking.get("paid_amount")),
        booking.get("transfer_ref") or "",
        booking.get("ticket_type") or "",
        "",  # ArrivalBoatBoarded
        "",  # DepartureBoatBoarded
        "",  # CheckinTime
        booking.get("status") or "booked",
        booking.get("id_doc_url") or "",
        booking.get("group_id") or "",
        created_at,
        updated_at,
    ]


def build_event_row(master_row: list) -> list:
    """
    Convert a MASTER row into an EVENT row (drops Event, reorders fields).
    Assumes master_row is aligned with MASTER_HEADERS.

    Mapping:
    - Master[2] TicketRef → Event["T. Reference"]
    - Master[4] IDNumber → Event["ID"]
    - Master[5] Phone → Event["Number"]
    - Master[6] MaleDep → Event["Male' Dep"]
    - Master[10] PaidAmount → Event["Paid Amount"]
    - Master[11] TransferRef → Event["Transfer slip Ref"]
    - Master[15] CheckinTime → Event["Check in Time"]
    - Master[17] ID Doc URL → Event["ID Doc URL"]
    - Master[8]/[9] Arrival/DepartureTime → Event["ArrivalTime"/"DepartureTime"]
    - Master[13]/[14] BoatBoarded → Event["ArrivalBoatBoarded"/"DepartureBoatBoarded"]
    """
    return [
        master_row[0],   # No
        master_row[2],   # TicketRef → T. Reference
        master_row[3],   # Name
        master_row[4],   # IDNumber → ID
        master_row[5],   # Phone → Number
        master_row[6],   # MaleDep → Male' Dep
        master_row[7],   # ResortDep
        master_row[10],  # PaidAmount
        master_row[11],  # TransferRef
        master_row[12],  # TicketType
        master_row[15],  # CheckinTime
        master_row[16],  # Status
        master_row[17],  # ID Doc URL
        master_row[8],   # ArrivalTime
        master_row[9],   # DepartureTime
        master_row[13],  # ArrivalBoatBoarded
        master_row[14],  # DepartureBoatBoarded
    ]
