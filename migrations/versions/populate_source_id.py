"""populate institution source_id

Revision ID: populate_source_id
Revises: 6d7cd43b5789
Create Date: 2026-03-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "populate_source_id"
down_revision: Union[str, Sequence[str], None] = "ec4fd92511f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Populate source_id for existing institutions"""
    openalex_source = (
        op.get_bind()
        .execute(sa.text("SELECT id FROM source WHERE name = 'openalex'"))
        .fetchone()
    )

    if openalex_source:
        source_id = openalex_source[0]
        op.execute(
            sa.text(
                f"UPDATE institution SET source_id = {source_id} WHERE source_id IS NULL"
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    pass
