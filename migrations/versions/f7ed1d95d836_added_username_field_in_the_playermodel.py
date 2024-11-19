"""Added username field in the PlayerModel

Revision ID: f7ed1d95d836
Revises: 86d52dde2ea2
Create Date: 2024-11-17 19:46:27.900064

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7ed1d95d836'
down_revision: Union[str, None] = '86d52dde2ea2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('players', sa.Column('username', sa.String(), nullable=False))
    op.create_unique_constraint(None, 'players', ['username'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'players', type_='unique')
    op.drop_column('players', 'username')
    # ### end Alembic commands ###