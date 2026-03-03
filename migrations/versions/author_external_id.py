"""use author_external_id in affiliation

Revision ID: author_external_id
Revises: populate_source_id
Create Date: 2026-03-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "author_external_id"
down_revision: Union[str, Sequence[str], None] = "populate_source_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add author_external_id column and populate it"""
    op.add_column(
        "affiliation", sa.Column("author_external_id", sa.String(), nullable=True)
    )
    op.execute(
        sa.text("""
            UPDATE affiliation 
            SET author_external_id = (
                SELECT external_id FROM author WHERE author.id = affiliation.author_id
            )
        """)
    )
    # Drop FK constraint first
    op.drop_constraint(None, "affiliation", type_="foreignkey")
    op.drop_column("affiliation", "author_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("affiliation", sa.Column("author_id", sa.Integer(), nullable=True))
    op.execute(
        sa.text("""
            UPDATE affiliation 
            SET author_id = (
                SELECT id FROM author WHERE author.external_id = affiliation.author_external_id
            )
        """)
    )
    op.create_foreign_key(None, "affiliation", "author", ["author_id"], ["id"])
    op.drop_column("affiliation", "author_external_id")
