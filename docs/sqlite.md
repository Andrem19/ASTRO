# SQLite Operations

The production database is a single SQLite file. The default path is:

```text
./data/astrology_mcp.sqlite3
```

Do not place the database in `/tmp` or any directory that can be cleaned by the
operating system. Use persistent server storage with normal filesystem backups.

## Backup

Create the backup directory:

```bash
mkdir -p ./backups
```

Run an online SQLite backup:

```bash
sqlite3 ./data/astrology_mcp.sqlite3 ".backup './backups/astrology_mcp_$(date +%Y%m%d_%H%M%S).sqlite3'"
```

The `.backup` command is safe to use while the service is running. It creates a
consistent copy without editing the live database file directly.

If `sqlite3` is not installed, install it with the Linux package manager:

```bash
sudo apt-get update
sudo apt-get install sqlite3
```

On RPM-based systems:

```bash
sudo dnf install sqlite
```

## Restore

Stop the service before restoring a database file:

```bash
sudo systemctl stop astrology-mcp
```

Copy the selected backup over the live database:

```bash
cp ./backups/backup-file.sqlite3 ./data/astrology_mcp.sqlite3
```

Start the service again:

```bash
sudo systemctl start astrology-mcp
```

Check the service:

```bash
sudo systemctl status astrology-mcp
curl http://127.0.0.1:8000/health
```

## Maintenance Rules

- Make regular backups.
- Do not edit the SQLite file by hand.
- Stop the service before manual restore.
- Do not store the database in `/tmp`.
- Do not log profile contents, private notes, full birth data, or chart JSON.
- Keep WAL, foreign keys, and busy timeout enabled through application settings.
- Do not write intermediate transit sampling data to the database.
- Cache only final chart results when cache use is explicitly needed.
