"""Generate ignored local configuration; never overwrite an existing .env."""

from pathlib import Path
from secrets import token_urlsafe

path = Path(".env")
if not path.exists():
    password = token_urlsafe(24)
    db_password = token_urlsafe(24)
    path.write_text(
        f"ROADEYE_DEMO_ENABLED=true\nROADEYE_DEMO_PASSWORD={password}\nROADEYE_DB_PASSWORD={db_password}\nROADEYE_DATABASE_URL=postgresql+psycopg://roadeye:{db_password}@localhost:5432/roadeye\nROADEYE_SOURCE_MODE=synthetic\n"
    )
    path.chmod(0o600)
    print("Created ignored .env with unique local credentials. Read it locally to sign in.")
else:
    print("Existing .env preserved.")
