"""add_event_id_to_booking_groups

Revision ID: a3fe4d5468b5
Revises: 615b5fc2b4ae
Create Date: 2025-10-01 21:22:56.376563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3fe4d5468b5'
down_revision: Union[str, None] = '615b5fc2b4ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
