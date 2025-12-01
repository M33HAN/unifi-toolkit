# Migration Guide: Wi-Fi Stalker → UniFi Toolkit

This guide helps you migrate from the standalone **Wi-Fi Stalker** application to the new **UniFi Toolkit** monorepo.

## Overview

UniFi Toolkit is a comprehensive collection of UniFi management tools, with Wi-Fi Stalker as the first integrated tool. The migration preserves all your existing data while providing a foundation for future tools.

## What's Changed

### New Structure

- **Monorepo**: Single repository housing multiple tools
- **Shared Infrastructure**: Common UniFi client, database, and configuration
- **Tool Prefix**: Database tables now use `stalker_` prefix
- **Unified Dashboard**: Main landing page with access to all tools
- **Tool Mounting**: Wi-Fi Stalker accessible at `/stalker/`

### Backwards Compatible

- ✅ All existing features preserved
- ✅ Same API endpoints (under `/stalker/api/`)
- ✅ Same database schema (with table prefix)
- ✅ Same UI and workflows
- ✅ Same configuration options

### New Features

- 🔧 Alembic database migrations
- 🐳 Improved Docker deployment
- 📊 Unified health check endpoint
- 🔌 WebSocket real-time updates
- 📦 Modular tool architecture

## Migration Steps

### Option 1: Fresh Installation (Recommended)

The easiest approach is to start fresh with UniFi Toolkit and re-add your devices.

1. **Stop the old Wi-Fi Stalker**:
   ```bash
   # If running as systemd service
   sudo systemctl stop wifi-stalker

   # If running with Docker
   docker-compose down

   # If running manually
   # Press Ctrl+C in the terminal
   ```

2. **Clone UniFi Toolkit**:
   ```bash
   git clone https://github.com/Crosstalk-Solutions/unifi-toolkit.git
   cd unifi-toolkit
   ```

3. **Set up environment**:
   ```bash
   # Copy environment template
   cp .env.example .env

   # Generate encryption key
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

   # Edit .env and add:
   # - ENCRYPTION_KEY (from above command)
   # - UniFi controller settings (optional, can configure via UI)
   nano .env
   ```

4. **Install and run**:

   **Native Python:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python run.py
   ```

   **Docker:**
   ```bash
   docker-compose up -d
   ```

5. **Access the application**:
   - Main dashboard: `http://localhost:8000`
   - Wi-Fi Stalker: `http://localhost:8000/stalker/`

6. **Re-add your devices**:
   - Navigate to Wi-Fi Stalker
   - Configure UniFi controller (same as before)
   - Use "Get Devices" to quickly select and track devices

### Option 2: Database Migration

If you have extensive history you want to preserve, you can migrate your database.

⚠️ **Warning**: This is an advanced procedure. Back up your data first!

1. **Backup your existing database**:
   ```bash
   cp ~/path/to/wifi-stalker/wifi_stalker.db ~/wifi_stalker_backup.db
   ```

2. **Clone and set up UniFi Toolkit** (follow steps 2-4 from Option 1)

3. **Copy and rename database**:
   ```bash
   # Copy old database to new location
   cp ~/wifi_stalker_backup.db ./data/unifi_toolkit.db
   ```

4. **Update table names** (using SQLite CLI):
   ```bash
   sqlite3 ./data/unifi_toolkit.db
   ```

   Run these SQL commands:
   ```sql
   -- Rename tables to use stalker_ prefix
   ALTER TABLE tracked_devices RENAME TO stalker_tracked_devices;
   ALTER TABLE connection_history RENAME TO stalker_connection_history;
   ALTER TABLE webhook_config RENAME TO stalker_webhook_config;

   -- Verify tables
   .tables

   -- Exit
   .quit
   ```

5. **Start the application**:
   ```bash
   python run.py
   ```

6. **Verify migration**:
   - Check that all devices appear in Wi-Fi Stalker
   - Verify connection history is intact
   - Test webhook configurations

### Option 3: Export/Import

For a clean migration with selective data preservation:

1. **Export data from old Wi-Fi Stalker**:
   - Open Wi-Fi Stalker UI
   - For each device, click to view details
   - Click "View History" and export to CSV
   - Save device MAC addresses and friendly names

2. **Set up new UniFi Toolkit** (follow Option 1, steps 1-5)

3. **Import devices**:
   - Navigate to Wi-Fi Stalker
   - Use "Get Devices" to quickly add devices
   - Or manually add using saved MAC addresses

## Configuration Migration

### Environment Variables

Old `.env` settings map to new ones:

| Old Variable | New Variable | Notes |
|--------------|-------------|-------|
| `ENCRYPTION_KEY` | `ENCRYPTION_KEY` | Same |
| `REFRESH_INTERVAL_SECONDS` | `STALKER_REFRESH_INTERVAL` | Renamed for clarity |
| `UNIFI_CONTROLLER_URL` | `UNIFI_CONTROLLER_URL` | Same |
| `UNIFI_USERNAME` | `UNIFI_USERNAME` | Same |
| `UNIFI_PASSWORD` | `UNIFI_PASSWORD` | Same |
| `UNIFI_API_KEY` | `UNIFI_API_KEY` | Same |
| `UNIFI_SITE_ID` | `UNIFI_SITE_ID` | Same |
| `UNIFI_VERIFY_SSL` | `UNIFI_VERIFY_SSL` | Same |
| `LOG_LEVEL` | `LOG_LEVEL` | Same |

### Docker Compose

Key changes in `docker-compose.yml`:

- **Service name**: `wifi-stalker` → `unifi-toolkit`
- **Container name**: `wifi-stalker` → `unifi-toolkit`
- **Volumes**: `./wifi_stalker.db` → `./data/`

## Post-Migration Checklist

- [ ] Application starts without errors
- [ ] Can access main dashboard at `http://localhost:8000`
- [ ] Can access Wi-Fi Stalker at `http://localhost:8000/stalker/`
- [ ] UniFi controller connection works
- [ ] All tracked devices appear
- [ ] Device status updates correctly
- [ ] Connection history is preserved (if using database migration)
- [ ] Webhooks still work
- [ ] Can add new devices
- [ ] Background refresh is working

## Troubleshooting

### Database Connection Issues

**Problem**: "No tracked devices" after migration

**Solution**: Verify table names have `stalker_` prefix:
```bash
sqlite3 ./data/unifi_toolkit.db ".tables"
```

Should show:
- `stalker_tracked_devices`
- `stalker_connection_history`
- `stalker_webhook_config`
- `unifi_config`

### ENCRYPTION_KEY Mismatch

**Problem**: "Failed to decrypt credentials"

**Solution**: You must use the **same ENCRYPTION_KEY** from your old installation. Check your old `.env` file and copy the key exactly.

### Import Errors

**Problem**: "ModuleNotFoundError" or import issues

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or rebuild Docker image
docker-compose build --no-cache
```

### Port Conflicts

**Problem**: "Address already in use"

**Solution**: Either stop the old Wi-Fi Stalker or change the port in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Use port 8001 instead
```

## Rollback Plan

If migration fails, you can rollback:

1. **Stop UniFi Toolkit**:
   ```bash
   docker-compose down
   # or
   # Press Ctrl+C if running natively
   ```

2. **Restore old Wi-Fi Stalker**:
   ```bash
   cd ~/path/to/old/wifi-stalker
   python run.py
   # or
   docker-compose up -d
   ```

3. **Restore database backup** (if you made one):
   ```bash
   cp ~/wifi_stalker_backup.db ./wifi_stalker.db
   ```

## Getting Help

If you encounter issues during migration:

1. Check the [README.md](../README.md) for setup instructions
2. Review [CLAUDE.md](../CLAUDE.md) for architecture details
3. Open an issue: https://github.com/Crosstalk-Solutions/unifi-toolkit/issues
4. Include:
   - Migration method used (Option 1, 2, or 3)
   - Error messages
   - Logs from `docker-compose logs` or console output

## Future Migrations

When new tools are added to UniFi Toolkit, no migration will be needed. Simply update the application:

```bash
# Pull latest changes
git pull

# Update dependencies
pip install -r requirements.txt

# Restart application
python run.py
```

Or with Docker:
```bash
docker-compose pull
docker-compose up -d
```

The toolkit handles tool additions automatically with no data loss.
