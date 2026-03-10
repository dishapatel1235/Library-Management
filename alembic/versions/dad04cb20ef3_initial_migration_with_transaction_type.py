"""initial migration with transaction_type (fixed)

Revision ID: dad04cb20ef3
Revises: 
Create Date: 2026-03-06 17:01:06.549446
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dad04cb20ef3'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Upgrade schema."""

    # Create enum type only if it doesn't exist
    transaction_type_enum = postgresql.ENUM('ISSUE', 'RENEW', 'RETURN', name='transactiontype', create_type=False)
    transaction_type_enum.create(op.get_bind(), checkfirst=True)

    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('member_id', sa.Integer(), sa.ForeignKey('members.id'), nullable=True),
        sa.Column('posting_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('transaction_type', transaction_type_enum, nullable=False)
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])

    # Create transaction_items table
    op.create_table(
        'transaction_items',
        sa.Column('transaction_id', sa.Integer(), sa.ForeignKey('transactions.id'), primary_key=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id'), primary_key=True)
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('transaction_items')
    op.drop_index('ix_transactions_id', table_name='transactions')
    op.drop_table('transactions')

    # Drop enum type if exists
    transaction_type_enum = postgresql.ENUM('ISSUE', 'RENEW', 'RETURN', name='transactiontype')
    transaction_type_enum.drop(op.get_bind(), checkfirst=True)