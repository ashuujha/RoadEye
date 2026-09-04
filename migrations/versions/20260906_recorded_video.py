"""Isolated recorded camera and durable inference tasks."""

import sqlalchemy as sa
from alembic import op

revision = "20260906_recorded"
down_revision = "20260905_immutable"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("runs_source_mode_check", "runs", type_="check")
    op.create_check_constraint(
        "runs_source_mode_check", "runs", "source_mode IN ('synthetic','recorded_real')"
    )
    for column in ("zone_id", "x", "y"):
        op.alter_column("cameras", column, nullable=True)
    op.create_table(
        "video_tasks",
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.id"), nullable=False, unique=True),
        sa.Column("recording_id", sa.String(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("progress", sa.JSON(), nullable=False),
    )
    op.execute("""
    CREATE FUNCTION roadeye_video_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.run_id IS DISTINCT FROM OLD.run_id OR NEW.recording_id IS DISTINCT FROM OLD.recording_id
         OR NEW.config::jsonb IS DISTINCT FROM OLD.config::jsonb THEN
        RAISE EXCEPTION 'Recording configuration is immutable';
      END IF;
      RETURN NEW;
    END; $$;
    CREATE TRIGGER immutable_video_scope BEFORE UPDATE ON video_tasks
      FOR EACH ROW EXECUTE FUNCTION roadeye_video_scope();
    """)


def downgrade():
    op.execute(
        "DROP TRIGGER immutable_video_scope ON video_tasks; DROP FUNCTION roadeye_video_scope();"
    )
    op.drop_table("video_tasks")
    # Refuse destructive downgrade when recorded runs/cameras exist.
    op.drop_constraint("runs_source_mode_check", "runs", type_="check")
    op.create_check_constraint("runs_source_mode_check", "runs", "source_mode = 'synthetic'")
    for column in ("zone_id", "x", "y"):
        op.alter_column("cameras", column, nullable=False)
