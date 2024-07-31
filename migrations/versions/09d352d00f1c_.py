"""empty message

Revision ID: 09d352d00f1c
Revises: 8e01b3322da7
Create Date: 2021-04-21 22:42:55.305898

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '09d352d00f1c'
down_revision = '8e01b3322da7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('credit_note',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date_change', sa.DateTime(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('difference', sa.Float(), nullable=True),
    sa.Column('outstanding', sa.Float(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_index('ix_public_temptable_index', table_name='temptable')
    op.drop_table('temptable')
    op.add_column('accounting_record', sa.Column('total_hours', sa.Float(), nullable=True))
    op.drop_column('accounting_record', 'hours_per_week')
    op.add_column('transaction', sa.Column('service_1_total_hours', sa.Float(), nullable=True))
    op.add_column('transaction', sa.Column('service_2_total_hours', sa.Float(), nullable=True))
    op.add_column('transaction', sa.Column('service_3_total_hours', sa.Float(), nullable=True))
    op.add_column('transaction', sa.Column('service_4_total_hours', sa.Float(), nullable=True))
    op.add_column('transaction', sa.Column('service_5_total_hours', sa.Float(), nullable=True))
    op.add_column('transaction', sa.Column('service_6_total_hours', sa.Float(), nullable=True))
    op.drop_column('transaction', 'service_4_hours_per_week')
    op.drop_column('transaction', 'service_6_hours_per_week')
    op.drop_column('transaction', 'service_3_hours_per_week')
    op.drop_column('transaction', 'service_2_hours_per_week')
    op.drop_column('transaction', 'service_5_hours_per_week')
    op.drop_column('transaction', 'service_1_hours_per_week')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transaction', sa.Column('service_1_hours_per_week', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('transaction', sa.Column('service_5_hours_per_week', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('transaction', sa.Column('service_2_hours_per_week', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('transaction', sa.Column('service_3_hours_per_week', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('transaction', sa.Column('service_6_hours_per_week', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('transaction', sa.Column('service_4_hours_per_week', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.drop_column('transaction', 'service_6_total_hours')
    op.drop_column('transaction', 'service_5_total_hours')
    op.drop_column('transaction', 'service_4_total_hours')
    op.drop_column('transaction', 'service_3_total_hours')
    op.drop_column('transaction', 'service_2_total_hours')
    op.drop_column('transaction', 'service_1_total_hours')
    op.add_column('accounting_record', sa.Column('hours_per_week', postgresql.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.drop_column('accounting_record', 'total_hours')
    op.create_table('temptable',
    sa.Column('index', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('name_th', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('school', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mom_mobile_num', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('know_us_from', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('streak_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mom_name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('email', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('universal_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('dad_name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('previous_scores', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('dad_mobile_num', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('address', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('dad_line', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('line', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mobile_num', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mom_line', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('tax_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('graduate_year', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('dad_email', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('mom_email', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('student_country', sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.create_index('ix_public_temptable_index', 'temptable', ['index'], unique=False)
    op.drop_table('credit_note')
    # ### end Alembic commands ###
