"""add_event_id_to_booking_groups

Revision ID: ec16ab983bf8
Revises: 97534aa52365
Create Date: 2025-10-01 21:08:37.824250

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec16ab983bf8'
down_revision: Union[str, None] = '97534aa52365'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
