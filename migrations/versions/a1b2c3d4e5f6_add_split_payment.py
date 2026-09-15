"""add split payment columns to orders

Revision ID: a1b2c3d4e5f6
Revises: 8f98c91b0a66
Create Date: 2026-04-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '8f98c91b0a66'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('commission_rate',   sa.Float(),      nullable=True))
        batch_op.add_column(sa.Column('commission_amount', sa.Float(),      nullable=True))
        batch_op.add_column(sa.Column('restaurant_amount', sa.Float(),      nullable=True))
        batch_op.add_column(sa.Column('split_status',      sa.String(30),   nullable=True, server_default='pending'))
        batch_op.add_column(sa.Column('split_done_at',     sa.DateTime(),   nullable=True))


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('split_done_at')
        batch_op.drop_column('split_status')
        batch_op.drop_column('restaurant_amount')
        batch_op.drop_column('commission_amount')
        batch_op.drop_column('commission_rate')
