import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import (
    fetch_pathways_for_admin,
    fetch_verified_pathways,
    get_connection,
    init_db,
    update_pathway,
)

p = init_db()
print("db", p)
conn = get_connection()
tables = [
    r[0]
    for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
]
print("tables", tables)
for table in ("licenses_tb", "funds_tb", "pathways_tb"):
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name=?", (table,)
    ).fetchone()[0]
    assert "Human_Verified INTEGER NOT NULL DEFAULT 0" in sql, table
    print(table, "Human_Verified default OK")

# Smoke-test write path with temp rows
conn.execute(
    "INSERT INTO licenses_tb (License_ID, Status, Human_Verified) VALUES ('GL_TEST', 'Active', 0)"
)
conn.execute(
    "INSERT INTO funds_tb (Fund_Name, Capital_Type, Human_Verified) VALUES ('Test Fund', 'Grant', 0)"
)
lic_id = conn.execute("SELECT id FROM licenses_tb WHERE License_ID='GL_TEST'").fetchone()[0]
fund_id = conn.execute("SELECT id FROM funds_tb WHERE Fund_Name='Test Fund'").fetchone()[0]
conn.execute(
    "INSERT INTO pathways_tb (Linked_Fund, Governing_License, Compliance_Verdict, Human_Verified) "
    "VALUES (?, ?, 'Yellow', 0)",
    (fund_id, lic_id),
)
conn.commit()
map_id = conn.execute("SELECT Map_ID FROM pathways_tb ORDER BY Map_ID DESC LIMIT 1").fetchone()[0]

assert len(fetch_verified_pathways()) == 0
update_pathway(map_id, "Green", True)
verified = fetch_verified_pathways()
assert len(verified) == 1
assert verified[0]["compliance_verdict"] == "Green"
assert verified[0]["human_verified"] is True
admin = fetch_pathways_for_admin()
assert any(r["map_id"] == map_id for r in admin)

# Cleanup smoke rows
conn.execute("DELETE FROM pathways_tb WHERE Map_ID=?", (map_id,))
conn.execute("DELETE FROM funds_tb WHERE id=?", (fund_id,))
conn.execute("DELETE FROM licenses_tb WHERE id=?", (lic_id,))
conn.commit()
print("smoke_ok")
