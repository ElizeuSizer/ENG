"""Adiciona coluna pedido_id em NotaFiscal

Revision ID: 33b1934c594a
Revises: 55ebe31f55fb
Create Date: 2025-02-26 12:42:43.103401

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '33b1934c594a'
down_revision = '55ebe31f55fb'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('nota_fiscal', schema=None) as batch_op:
        # Adiciona a coluna 'pedido_id'
        batch_op.add_column(sa.Column('pedido_id', sa.Integer(), nullable=True))
        # Cria a constraint de chave estrangeira com um nome definido
        batch_op.create_foreign_key('fk_nota_fiscal_pedido_id', 'pedido', ['pedido_id'], ['id'])

def downgrade():
    with op.batch_alter_table('nota_fiscal', schema=None) as batch_op:
        # Remove a constraint e depois a coluna
        batch_op.drop_constraint('fk_nota_fiscal_pedido_id', type_='foreignkey')
        batch_op.drop_column('pedido_id')
