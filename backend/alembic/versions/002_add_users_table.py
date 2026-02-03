"""Add users table for authentication

Revision ID: 002_add_users_table
Revises: 001_initial_schema
Create Date: 2026-02-03 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_users_table'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user role enum
    user_role = postgresql.ENUM('viewer', 'accountant', 'approver', 'admin', name='user_role')
    user_role.create(op.get_bind(), checkfirst=True)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.Enum('viewer', 'accountant', 'approver', 'admin', name='user_role'), 
                  nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_email_active', 'users', ['email', 'is_active'])
    op.create_index('ix_users_role', 'users', ['role'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_users_role', table_name='users')
    op.drop_index('ix_users_email_active', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    
    # Drop table
    op.drop_table('users')
    
    # Drop enum
    user_role = postgresql.ENUM('viewer', 'accountant', 'approver', 'admin', name='user_role')
    user_role.drop(op.get_bind(), checkfirst=True)
