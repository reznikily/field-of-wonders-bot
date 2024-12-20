"""Updated game model

Revision ID: 86d52dde2ea2
Revises: 5fc8040ef224
Create Date: 2024-11-16 20:28:44.992488

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "86d52dde2ea2"
down_revision: Union[str, None] = "5fc8040ef224"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "games", sa.Column("word_state", sa.BigInteger(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("games", "word_state")
    # ### end Alembic commands ###
