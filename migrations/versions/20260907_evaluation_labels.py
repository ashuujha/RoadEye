"""Human evaluation labels are separate immutable revisions, not inference answers."""

import sqlalchemy as sa
from alembic import op

revision = "20260907_labels"
down_revision = "20260906_recorded"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "evaluation_labels",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("passage_id", sa.String(), sa.ForeignKey("vehicle_passages.id")),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("reviewer_name", sa.String(), nullable=False),
        sa.Column("label", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "target", "revision"),
        sa.CheckConstraint("revision > 0"),
    )
    op.create_index("ix_evaluation_labels_run_id", "evaluation_labels", ["run_id"])
    op.execute(
        "CREATE TRIGGER immutable_evaluation BEFORE UPDATE OR DELETE ON evaluation_labels FOR EACH ROW EXECUTE FUNCTION roadeye_immutable()"
    )


def downgrade():
    op.drop_table("evaluation_labels")
