"""Add wiki_root column to expert table

Revision ID: add_wiki_root_to_expert
Revises: f6a7b8c9d0e1
Create Date: 2026-04-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'add_wiki_root_to_expert'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add wiki_root column to expert table
    op.add_column(
        'expert',
        sa.Column('wiki_root', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('expert', 'wiki_root')