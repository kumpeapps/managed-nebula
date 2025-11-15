"""add docker_compose_template to global_settings

Revision ID: 202511132147
Revises: fd03ead652bc
Create Date: 2025-11-13 21:47:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '202511132147'
down_revision = 'fd03ead652bc'
branch_labels = None
depends_on = None


# Default docker-compose template
DEFAULT_DOCKER_COMPOSE_TEMPLATE = """version: '3.8'

services:
  nebula-client:
    image: {{CLIENT_DOCKER_IMAGE}}
    container_name: nebula-{{CLIENT_NAME}}
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    environment:
      SERVER_URL: {{SERVER_URL}}
      CLIENT_TOKEN: {{CLIENT_TOKEN}}
      POLL_INTERVAL_HOURS: {{POLL_INTERVAL_HOURS}}
    volumes:
      - ./nebula-config:/etc/nebula
      - ./nebula-data:/var/lib/nebula
    network_mode: host"""


def upgrade() -> None:
    # Add docker_compose_template column to global_settings table
    op.add_column('global_settings', 
        sa.Column('docker_compose_template', sa.Text(), nullable=True)
    )
    
    # Set default value for existing rows using parameterized query
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE global_settings SET docker_compose_template = :template WHERE docker_compose_template IS NULL"),
        {"template": DEFAULT_DOCKER_COMPOSE_TEMPLATE}
    )


def downgrade() -> None:
    # Remove docker_compose_template column
    op.drop_column('global_settings', 'docker_compose_template')
