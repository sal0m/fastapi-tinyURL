"""renamed tables

Revision ID: c773a6841446
Revises: a4e3ac9c8287
Create Date: 2025-03-22 17:06:58.924049

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c773a6841446'
down_revision: Union[str, None] = 'a4e3ac9c8287'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Удаляем старые таблицы с CASCADE
    op.execute('DROP TABLE IF EXISTS users CASCADE')
    op.execute('DROP TABLE IF EXISTS urls CASCADE')

    # Создаем новую таблицу user
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('registered_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_user_id'), 'user', ['id'], unique=False)

    # Создаем новую таблицу url
    op.create_table('url',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_url', sa.String(), nullable=False),
        sa.Column('short_code', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('custom_alias', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('custom_alias'),
        sa.UniqueConstraint('short_code')
    )
    op.create_index(op.f('ix_url_id'), 'url', ['id'], unique=False)

    # Удаляем старый внешний ключ, если он существует
    # Замените 'stats_url_id_fkey' на правильное имя ограничения, если оно отличается
    op.execute('ALTER TABLE stats DROP CONSTRAINT IF EXISTS stats_url_id_fkey')

    # Создаем новый внешний ключ
    op.create_foreign_key(None, 'stats', 'url', ['url_id'], ['id'])


def downgrade() -> None:
    # Удаляем новый внешний ключ
    op.drop_constraint(None, 'stats', type_='foreignkey')

    # Восстанавливаем старый внешний ключ
    op.create_foreign_key('stats_url_id_fkey', 'stats', 'urls', ['url_id'], ['id'])

    # Удаляем новые таблицы
    op.drop_table('url')
    op.drop_table('user')

    # Восстанавливаем старые таблицы
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('registered_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)

    op.create_table('urls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_url', sa.String(), nullable=False),
        sa.Column('short_code', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('custom_alias', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('custom_alias'),
        sa.UniqueConstraint('short_code')
    )
    op.create_index('ix_urls_id', 'urls', ['id'], unique=False)
