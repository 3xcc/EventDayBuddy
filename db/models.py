from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# ===== Core Booking =====
class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)  # T. Reference
    event_name = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    id_number = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True, index=True)
    male_dep = Column(String, nullable=True)
    resort_dep = Column(String, nullable=True)
    paid_amount = Column(Numeric, nullable=True)
    transfer_ref = Column(String, nullable=True)
    ticket_type = Column(String, nullable=True)
    checkin_time = Column(DateTime(timezone=True), nullable=True)
    boat = Column(Integer, ForeignKey("boats.boat_number"), nullable=True, index=True)
    status = Column(String, default="booked", index=True)  # booked / boarded / missed / transferred
    id_doc_url = Column(String, nullable=True)

    group_id = Column(Integer, ForeignKey("booking_groups.id"), nullable=True)
    group = relationship("BookingGroup", back_populates="bookings")

    boat_rel = relationship("Boat", back_populates="bookings")
    checkins = relationship("CheckinLog", back_populates="booking")

    def __repr__(self):
        return f"<Booking id={self.id} name={self.name} event={self.event_name} status={self.status}>"

# ===== Booking Group =====
class BookingGroup(Base, TimestampMixin):
    __tablename__ = "booking_groups"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bookings = relationship("Booking", back_populates="group")

    def __repr__(self):
        return f"<BookingGroup id={self.id} phone={self.phone}>"

# ===== Ticket Transfer Log =====
class TicketTransferLog(Base, TimestampMixin):
    __tablename__ = "ticket_transfer_logs"

    id = Column(Integer, primary_key=True, index=True)
    from_booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    to_booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    transferred_by = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String, nullable=True)

    def __repr__(self):
        return f"<TicketTransferLog from={self.from_booking_id} to={self.to_booking_id}>"

# ===== Boat Inventory =====
class Boat(Base, TimestampMixin):
    __tablename__ = "boats"

    id = Column(Integer, primary_key=True, index=True)
    boat_number = Column(Integer, nullable=False, unique=True, index=True)
    capacity = Column(Integer, nullable=False)
    status = Column(String, default="open", index=True)

    bookings = relationship("Booking", back_populates="boat_rel")
    sessions = relationship("BoardingSession", back_populates="boat_rel")

    def __repr__(self):
        return f"<Boat number={self.boat_number} capacity={self.capacity} status={self.status}>"

# ===== Telegram User Roles =====
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=True)
    role = Column(String, default="viewer")  # admin / checkin_staff / booking_staff / viewer

    sessions_started = relationship("BoardingSession", back_populates="user_rel")

    def __repr__(self):
        return f"<User chat_id={self.chat_id} role={self.role}>"

# ===== Config Store =====
class Config(Base, TimestampMixin):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)

    def __repr__(self):
        return f"<Config {self.key}={self.value}>"

# ===== Boarding Session Tracker =====
class BoardingSession(Base, TimestampMixin):
    __tablename__ = "boarding_sessions"

    id = Column(Integer, primary_key=True, index=True)
    boat_number = Column(Integer, ForeignKey("boats.boat_number"), nullable=False, index=True)
    event_name = Column(String, nullable=True)
    started_by = Column(String, ForeignKey("users.chat_id"), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    boat_rel = relationship("Boat", back_populates="sessions")
    user_rel = relationship("User", back_populates="sessions_started")

    def __repr__(self):
        return f"<BoardingSession boat={self.boat_number} event={self.event_name} active={self.is_active}>"

# ===== Check-in Log =====
class CheckinLog(Base, TimestampMixin):
    __tablename__ = "checkin_logs"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    boat_number = Column(Integer, ForeignKey("boats.boat_number"), nullable=False)
    confirmed_by = Column(String, ForeignKey("users.chat_id"), nullable=False)
    method = Column(String, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), server_default=func.now())

    booking = relationship("Booking", back_populates="checkins")

    def __repr__(self):
        return f"<CheckinLog booking_id={self.booking_id} boat={self.boat_number} method={self.method}>"

# ===== Waitlist Tracker =====
class WaitlistEntry(Base, TimestampMixin):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    reason = Column(String, nullable=True)
    reassigned_boat = Column(Integer, ForeignKey("boats.boat_number"), nullable=True)
    notes = Column(String, nullable=True)

    def __repr__(self):
        return f"<WaitlistEntry booking_id={self.booking_id} reassigned_boat={self.reassigned_boat}>"
