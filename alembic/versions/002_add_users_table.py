"""Add users table for authentication

Revision ID: 002
Revises: 001
Create Date: 2025-12-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add users table."""
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('username', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), default='member', nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('is_superuser', sa.Boolean, default=False, nullable=False),
        sa.Column('email_verified', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime, nullable=True),
    )

    # Create indexes
    op.create_index('ix_users_organization_id', 'users', ['organization_id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])


def downgrade() -> None:
    """Remove users table."""
    op.drop_index('ix_users_username')
    op.drop_index('ix_users_email')
    op.drop_index('ix_users_organization_id')
    op.drop_table('users')
