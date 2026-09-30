"""init tables

Revision ID: 001_init
Revises:
Create Date: 2026-09-28
"""

from alembic import op

from app.core.database import Base
from app.models import tables  # noqa: F401

revision = "001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
