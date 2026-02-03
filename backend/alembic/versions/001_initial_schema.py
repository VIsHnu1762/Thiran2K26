"""Initial schema - Create all tables

Revision ID: 001
Revises: 
Create Date: 2026-02-03

This migration creates the initial database schema for BillAgent Pro:
- vendors: Store vendor/supplier information
- bills: Store bill header data
- line_items: Store individual items from bills
- audit_logs: Track all changes for compliance
- gl_codes: General ledger codes for accounting
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Enable PostgreSQL extensions
    # -------------------------------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    
    # -------------------------------------------------------------------------
    # Create vendors table
    # -------------------------------------------------------------------------
    op.create_table(
        'vendors',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('default_gl_code', sa.String(50), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('tax_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vendors_id', 'vendors', ['id'])
    op.create_index('ix_vendors_name', 'vendors', ['name'])
    
    # -------------------------------------------------------------------------
    # Create gl_codes table
    # -------------------------------------------------------------------------
    op.create_table(
        'gl_codes',
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False, server_default='EXPENSE'),
        sa.Column('parent_code', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('code')
    )
    
    # -------------------------------------------------------------------------
    # Create bills table
    # -------------------------------------------------------------------------
    bill_status_enum = postgresql.ENUM(
        'PROCESSING', 'NEEDS_REVIEW', 'APPROVED', 'POSTED', 'FAILED', 'DUPLICATE',
        name='billstatus',
        create_type=True
    )
    bill_status_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table(
        'bills',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invoice_number', sa.String(100), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=True),
        sa.Column('tax_amount', sa.Numeric(12, 2), nullable=True, server_default='0.00'),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('status', bill_status_enum, nullable=False, server_default='PROCESSING'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('field_confidence', postgresql.JSONB(), nullable=True),
        sa.Column('validation_errors', postgresql.JSONB(), nullable=True),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('duplicate_of_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('ocr_raw_data', postgresql.JSONB(), nullable=True),
        sa.Column('bounding_boxes', postgresql.JSONB(), nullable=True),
        sa.Column('task_id', sa.String(100), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('ocr_engine', sa.String(50), nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)', name='ck_confidence_score_range')
    )
    op.create_index('ix_bills_id', 'bills', ['id'])
    op.create_index('ix_bills_vendor_id', 'bills', ['vendor_id'])
    op.create_index('ix_bills_invoice_number', 'bills', ['invoice_number'])
    op.create_index('ix_bills_task_id', 'bills', ['task_id'])
    op.create_index('idx_bills_status', 'bills', ['status'])
    op.create_index('idx_bills_invoice_date', 'bills', ['invoice_date'])
    op.create_index('idx_bills_duplicate_check', 'bills', ['vendor_id', 'invoice_number', 'total_amount'])
    
    # -------------------------------------------------------------------------
    # Create line_items table
    # -------------------------------------------------------------------------
    op.create_table(
        'line_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 3), nullable=False, server_default='1.000'),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('total_price', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('tax_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('gl_code', sa.String(50), nullable=True),
        sa.Column('gl_code_source', sa.String(50), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('field_confidence', postgresql.JSONB(), nullable=True),
        sa.Column('bounding_box', postgresql.JSONB(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('has_math_error', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)', name='ck_line_item_confidence_range')
    )
    op.create_index('ix_line_items_id', 'line_items', ['id'])
    op.create_index('ix_line_items_bill_id', 'line_items', ['bill_id'])
    op.create_index('idx_line_items_gl_code', 'line_items', ['gl_code'])
    op.create_index('idx_line_items_bill_order', 'line_items', ['bill_id', 'sort_order'])
    
    # -------------------------------------------------------------------------
    # Create audit_logs table
    # -------------------------------------------------------------------------
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('bill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('agent_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('field_name', sa.String(100), nullable=True),
        sa.Column('old_value', postgresql.JSONB(), nullable=True),
        sa.Column('new_value', postgresql.JSONB(), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_bill_id', 'audit_logs', ['bill_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_agent', 'audit_logs', ['agent_name'])
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_bill_timestamp', 'audit_logs', ['bill_id', 'timestamp'])
    
    # -------------------------------------------------------------------------
    # Seed default GL codes
    # -------------------------------------------------------------------------
    op.execute("""
        INSERT INTO gl_codes (code, name, category, keywords) VALUES
        ('5001', 'Office Supplies', 'EXPENSE', 'office,supplies,paper,pen,pencil,stapler,folder,stationery,printer'),
        ('5002', 'Travel & Transportation', 'EXPENSE', 'travel,transport,fuel,gas,petrol,diesel,taxi,uber,flight,train,bus'),
        ('5003', 'Utilities', 'EXPENSE', 'utility,utilities,electric,electricity,water,gas,internet,phone,telecom'),
        ('5004', 'Professional Services', 'EXPENSE', 'professional,consulting,legal,accounting,audit,advisory,service'),
        ('5005', 'Maintenance & Repairs', 'EXPENSE', 'maintenance,repair,fix,service,cleaning,janitorial'),
        ('5006', 'Raw Materials', 'EXPENSE', 'raw,material,ingredient,component,supply,manufacturing'),
        ('5007', 'Inventory Purchases', 'EXPENSE', 'inventory,stock,goods,merchandise,product,purchase'),
        ('5008', 'Marketing & Advertising', 'EXPENSE', 'marketing,advertising,ad,promotion,campaign,media,print'),
        ('5009', 'Insurance', 'EXPENSE', 'insurance,premium,coverage,policy'),
        ('5010', 'Rent & Lease', 'EXPENSE', 'rent,lease,rental,property,office,warehouse'),
        ('5011', 'Equipment', 'EXPENSE', 'equipment,machine,machinery,tool,hardware,computer'),
        ('5012', 'Software & Subscriptions', 'EXPENSE', 'software,subscription,license,saas,cloud,app'),
        ('5099', 'Miscellaneous Expenses', 'EXPENSE', 'misc,miscellaneous,other')
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('audit_logs')
    op.drop_table('line_items')
    op.drop_table('bills')
    op.drop_table('gl_codes')
    op.drop_table('vendors')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS billstatus')
