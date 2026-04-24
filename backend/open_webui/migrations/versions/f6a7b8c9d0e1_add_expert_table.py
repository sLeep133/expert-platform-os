"""Add expert table

Revision ID: f6a7b8c9d0e1
Revises: 56359461a091
Create Date: 2026-04-24 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = '56359461a091'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if 'expert' not in existing_tables:
        op.create_table(
            'expert',
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('avatar', sa.Text(), nullable=True),
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('visibility', sa.Text(), nullable=False),
            sa.Column('persona_role', sa.Text(), nullable=True),
            sa.Column('persona_tone', sa.Text(), nullable=True),
            sa.Column('persona_style', sa.Text(), nullable=True),
            sa.Column('persona_constraints', sa.JSON(), nullable=True),
            sa.Column('method_principles', sa.JSON(), nullable=True),
            sa.Column('method_workflows', sa.JSON(), nullable=True),
            sa.Column('method_output_preferences', sa.JSON(), nullable=True),
            sa.Column('runtime_model', sa.Text(), nullable=True),
            sa.Column('runtime_provider', sa.Text(), nullable=True),
            sa.Column('runtime_context_budget', sa.BigInteger(), nullable=True),
            sa.Column('runtime_tool_policy', sa.Text(), nullable=False),
            sa.Column('runtime_collaboration_mode', sa.Text(), nullable=False),
            sa.Column('knowledge_spaces', sa.JSON(), nullable=True),
            sa.Column('knowledge_pinned_pages', sa.JSON(), nullable=True),
            sa.Column('knowledge_source_filters', sa.JSON(), nullable=True),
            sa.Column('system_prompt', sa.Text(), nullable=True),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('idx_expert_user_id', 'expert', ['user_id'])
        op.create_index('idx_expert_updated_at', 'expert', ['updated_at'])
        op.create_index('idx_expert_visibility', 'expert', ['visibility'])


def downgrade() -> None:
    op.drop_index('idx_expert_visibility', table_name='expert')
    op.drop_index('idx_expert_updated_at', table_name='expert')
    op.drop_index('idx_expert_user_id', table_name='expert')
    op.drop_table('expert')
