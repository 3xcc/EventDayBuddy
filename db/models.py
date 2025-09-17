from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)  # T. Reference
    event_name = Column(String, nullable=False)         # For Master sheet Event column
    name = Column(String, nullable=False)               # Name
    id_number = Column(String, nullable=False)          # ID
    phone = Column(String, nullable=True)               # Number
    male_dep = Column(String, nullable=True)            # Male' Dep
    resort_dep = Column(String, nullable=True)          # Resort Dep
    paid_amount = Column(Numeric, nullable=True)        # Paid Amount
    transfer_ref = Column(String, nullable=True)        # Transfer slip Ref
    ticket_type = Column(String, nullable=True)         # Ticket Type
    checkin_time = Column(DateTime(timezone=True), nullable=True)  # Check in Time
    boat = Column(String, nullable=True)                # Boat
    status = Column(String, default="booked")           # booked / checked-in / cancelled
    id_doc_url = Column(String, nullable=True)          # Google Drive link

class Boat(Base, TimestampMixin):
    __tablename__ = "boats"

    id = Column(Integer, primary_key=True, index=True)
    boat_number = Column(Integer, nullable=False, unique=True)
    capacity = Column(Integer, nullable=False)
    status = Column(String, default="open")  # open / departed

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=True)
    role = Column(String, default="viewer")  # admin / checkin_staff / booking_staff / viewer

class Config(Base, TimestampMixin):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)