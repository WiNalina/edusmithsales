"""empty message

Revision ID: 448bc4af5be4
Revises: 246c18f4199c
Create Date: 2021-04-08 21:24:50.890944

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '448bc4af5be4'
down_revision = '246c18f4199c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_public_temptable_index', table_name='temptable')
    op.drop_table('temptable')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('temptable',
    sa.Column('index', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('dad_line', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mobile_num', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('dad_mobile_num', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mom_email', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('line', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mom_mobile_num', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('tax_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('school', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mom_name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mom_line', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('graduate_year', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('streak_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('name_th', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('previous_scores', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('dad_email', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('universal_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('dad_name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('know_us_from', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('address', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('email', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('student_country', sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.create_index('ix_public_temptable_index', 'temptable', ['index'], unique=False)
    # ### end Alembic commands ###
