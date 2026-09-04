"""Enforce raw provenance and audit immutability at the database boundary."""

from alembic import op

revision = "20260905_immutable"
down_revision = "16336384d593"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE FUNCTION roadeye_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'RoadEye immutable record: %', TG_TABLE_NAME; END; $$;
    CREATE TRIGGER immutable_input BEFORE UPDATE ON input_events
      FOR EACH ROW EXECUTE FUNCTION roadeye_immutable();
    CREATE TRIGGER immutable_machine BEFORE UPDATE ON observations
      FOR EACH ROW EXECUTE FUNCTION roadeye_immutable();
    CREATE TRIGGER immutable_audit BEFORE UPDATE OR DELETE ON audit_records
      FOR EACH ROW EXECUTE FUNCTION roadeye_immutable();
    CREATE FUNCTION roadeye_run_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.source_mode IS DISTINCT FROM OLD.source_mode
         OR NEW.dataset_id IS DISTINCT FROM OLD.dataset_id
         OR NEW.network IS DISTINCT FROM OLD.network
         OR NEW.graph::jsonb IS DISTINCT FROM OLD.graph::jsonb THEN
        RAISE EXCEPTION 'Run provenance and graph snapshot are immutable';
      END IF;
      RETURN NEW;
    END; $$;
    CREATE TRIGGER immutable_run_scope BEFORE UPDATE ON runs
      FOR EACH ROW EXECUTE FUNCTION roadeye_run_scope();
    """)


def downgrade():
    op.execute("DROP TRIGGER immutable_run_scope ON runs; DROP FUNCTION roadeye_run_scope();")
    op.execute(
        "DROP TRIGGER immutable_input ON input_events; DROP TRIGGER immutable_machine ON observations; DROP TRIGGER immutable_audit ON audit_records; DROP FUNCTION roadeye_immutable();"
    )
