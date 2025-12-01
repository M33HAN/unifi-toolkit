# UniFi Toolkit

A suite of tools for UniFi network management, including device tracking, IDS monitoring, and AI-powered product recommendations.

## Tools

### Wi-Fi Stalker 📡
Track specific Wi-Fi client devices through UniFi infrastructure, monitor their connection status and roaming behavior.

**Status:** Active

### IDS Monitor 🛡️
View blocked IPs and intrusion detection/prevention system events from your UniFi network.

**Status:** Coming Soon

### Product Recommender 🤖
AI-powered UniFi product recommendations based on your environment and needs.

**Status:** Planned

## Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone git@github.com:Crosstalk-Solutions/unifi-toolkit.git
cd unifi-toolkit

# Create .env file
cp .env.example .env
# Edit .env and add your ENCRYPTION_KEY

# Start with Docker Compose
docker compose up -d
```

Access the toolkit at `http://localhost:8000`

### Manual Installation

```bash
# Clone the repository
git clone git@github.com:Crosstalk-Solutions/unifi-toolkit.git
cd unifi-toolkit

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your ENCRYPTION_KEY

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Start the application
python run.py
```

Access the toolkit at `http://localhost:8000`

## Configuration

### Required Settings

- `ENCRYPTION_KEY`: Required for encrypting UniFi credentials. Generate with:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

### Optional Settings

UniFi controller settings can be configured via `.env` file OR through the web UI (web UI takes precedence):

- `UNIFI_CONTROLLER_URL`: Your UniFi controller URL
- `UNIFI_USERNAME`: UniFi controller username
- `UNIFI_PASSWORD`: UniFi controller password (for legacy controllers)
- `UNIFI_API_KEY`: UniFi API key (for UniFi OS devices like UDM, UCG-Fiber)
- `UNIFI_SITE_ID`: UniFi site ID (default: "default")
- `UNIFI_VERIFY_SSL`: SSL verification (default: false for self-signed certs)

### Tool-Specific Settings

- `STALKER_REFRESH_INTERVAL`: Wi-Fi Stalker device refresh interval in seconds (default: 60)

See `.env.example` for all available settings.

## Architecture

UniFi Toolkit is a monorepo containing multiple tools:

```
unifi-toolkit/
├── shared/              # Shared infrastructure (UniFi API client, database, etc.)
├── tools/
│   ├── wifi_stalker/    # Device tracking tool
│   ├── ids_monitor/     # IDS monitoring tool (coming soon)
│   └── product_recommender/  # Product recommendation tool (planned)
├── app/                 # Main application assembly
└── templates/           # Unified dashboard
```

Each tool is independently developed but shares common infrastructure. The toolkit runs as a single FastAPI application with tools mounted at separate URL paths.

## Migrating from Wi-Fi Stalker

If you're currently using the standalone wifi-stalker application, see [docs/MIGRATION.md](docs/MIGRATION.md) for migration instructions.

## Requirements

- **Python:** 3.9-3.12 (Python 3.13+ not yet supported due to aiounifi dependency)
- **UniFi Controller:** Any version (supports both legacy and UniFi OS authentication)

## Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linters
black .
ruff check .
mypy .

# Run database migrations
alembic upgrade head

# Create new migration
alembic revision -m "Description of changes"
```

## Troubleshooting

### Can't connect to UniFi controller

- **Check controller URL**: Ensure `UNIFI_CONTROLLER_URL` is correct and accessible
- **SSL verification**: Set `UNIFI_VERIFY_SSL=false` for self-signed certificates
- **Authentication**: UniFi OS devices (UDM, UCG-Fiber) require an API key instead of username/password

### Device not showing as online

- Wait 60 seconds for the next refresh cycle
- Verify the MAC address is correct
- Check that the device is actually connected in the UniFi dashboard
- Enable DEBUG logging (`LOG_LEVEL=DEBUG`) to see active clients

### Database errors

- Backup your database: `cp data/unifi_toolkit.db data/unifi_toolkit.db.backup`
- Run migrations: `alembic upgrade head`
- If issues persist, check the logs for specific error messages

### Docker issues

- Check logs: `docker compose logs`
- Verify `.env` file exists and contains `ENCRYPTION_KEY`
- Ensure port 8000 is not already in use

## Support

- **Issues:** https://github.com/Crosstalk-Solutions/unifi-toolkit/issues
- **Discussions:** https://github.com/Crosstalk-Solutions/unifi-toolkit/discussions

## License

MIT License - See LICENSE file for details

## Credits

Developed by [Crosstalk Solutions](https://www.crosstalksolutions.com/)

- YouTube: [@CrosstalkSolutions](https://www.youtube.com/@CrosstalkSolutions)
- Website: https://www.crosstalksolutions.com/
