"""Rename gazette table to web-scraped-gazette

Revision ID: f7c0f7ce21db
Revises: 79330d9ee05c
Create Date: 2016-07-13 12:30:57.245001

"""

# revision identifiers, used by Alembic.
revision = 'f7c0f7ce21db'
down_revision = '79330d9ee05c'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.rename_table('gazettes', 'web_scraped_gazette')


def downgrade():
    op.rename_table('web_scraped_gazette', 'gazettes')
