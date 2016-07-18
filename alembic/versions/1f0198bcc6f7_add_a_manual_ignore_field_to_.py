"""Add a manual ignore field to WebScrapedGazette

Revision ID: 1f0198bcc6f7
Revises: 788cdc88f188
Create Date: 2016-07-15 00:31:20.314564

"""

# revision identifiers, used by Alembic.
revision = '1f0198bcc6f7'
down_revision = '788cdc88f188'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('web_scraped_gazette', sa.Column('manually_ignored', sa.Boolean(), nullable=True))
    op.execute('update web_scraped_gazette set manually_ignored = false')
    op.alter_column('web_scraped_gazette', 'manually_ignored', nullable=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('web_scraped_gazette', 'manually_ignored')
    ### end Alembic commands ###