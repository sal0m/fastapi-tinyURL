"""change_user_id_to_uuid

Revision ID: 282a05c37f44
Revises: ec447078b3b6
Create Date: 2025-03-23 14:16:01.651894

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision: str = '282a05c37f44'
down_revision: Union[str, None] = 'ec447078b3b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Включаем расширение uuid-ossp для генерации UUID
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Добавляем временный столбец для хранения UUID
    op.add_column('user', sa.Column('new_id', sa.UUID(), nullable=True))

    # Генерируем UUID для каждой строки и заполняем временный столбец
    op.execute('UPDATE "user" SET new_id = uuid_generate_v4()')

    # Удаляем старый столбец id
    op.drop_column('user', 'id')

    # Переименовываем временный столбец в id
    op.alter_column('user', 'new_id', new_column_name='id', nullable=False)

    # Делаем новый столбец id первичным ключом
    op.create_primary_key('pk_user', 'user', ['id'])


def downgrade() -> None:
    # Добавляем временный столбец для хранения INTEGER
    op.add_column('user', sa.Column('new_id', sa.Integer(), nullable=True))

    # Преобразуем UUID обратно в INTEGER (пример, нужно адаптировать под ваши данные)
    op.execute('UPDATE "user" SET new_id = (random() * 1000000)::int')  # Пример, нужно адаптировать

    # Удаляем старый столбец id
    op.drop_column('user', 'id')

    # Переименовываем временный столбец в id
    op.alter_column('user', 'new_id', new_column_name='id', nullable=False)

    # Делаем новый столбец id первичным ключом
    op.create_primary_key('pk_user', 'user', ['id'])