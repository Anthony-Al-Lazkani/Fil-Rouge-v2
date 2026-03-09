"""empty message

Revision ID: ec4fd92511f5
Revises: 6d7cd43b5789
Create Date: 2026-02-21 20:43:27.230851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec4fd92511f5'
down_revision: Union[str, Sequence[str], None] = '6d7cd43b5789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
