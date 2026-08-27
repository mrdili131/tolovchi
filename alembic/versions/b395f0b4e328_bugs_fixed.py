"""bugs fixed

Revision ID: b395f0b4e328
Revises: 36d368912e25
Create Date: 2026-08-27 09:36:26.970203

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b395f0b4e328'
down_revision: Union[str, Sequence[str], None] = '36d368912e25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("receiver_id", sa.Integer(), nullable=True)
        )

        batch_op.create_foreign_key(
            "fk_transactions_receiver_id_users",
            "users",
            ["receiver_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_transactions_receiver_id_users",
            type_="foreignkey",
        )

        batch_op.drop_column("receiver_id")