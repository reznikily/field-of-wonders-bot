"""Added game_state with enum type to the PlayerModel

Revision ID: ad80392e1d4b
Revises: c794cda72606
Create Date: 2024-11-18 17:38:56.993129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ad80392e1d4b'
down_revision: Union[str, None] = 'c794cda72606'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('games', sa.Column('game_state', postgresql.ENUM('ENDED', 'ACTIVE', name='gamestate'), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('games', 'game_state')
    # ### end Alembic commands ###