"""widen external_id to text

Revision ID: a1b2c3d4e5f6
Revises: 932dfd9038e9
Create Date: 2026-03-15 23:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str]] = "932dfd9038e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "articles",
        "external_id",
        existing_type=sa.String(255),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "articles",
        "author",
        existing_type=sa.String(255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "articles",
        "author",
        existing_type=sa.Text(),
        type_=sa.String(255),
        existing_nullable=True,
    )
    op.alter_column(
        "articles",
        "external_id",
        existing_type=sa.Text(),
        type_=sa.String(255),
        existing_nullable=False,
    )
