"""Allow volume_number to be null

Revision ID: 9310964bece4
Revises: 1f0198bcc6f7
Create Date: 2016-07-15 01:01:01.261242

"""

# revision identifiers, used by Alembic.
revision = '9310964bece4'
down_revision = '1f0198bcc6f7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('archived_gazette', 'volume_number',
               existing_type=sa.INTEGER(),
               nullable=True)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('archived_gazette', 'volume_number',
               existing_type=sa.INTEGER(),
               nullable=False)
    ### end Alembic commands ###
