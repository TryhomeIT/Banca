# 📰 Banca - Your Digital Newsstand

## About Banca

**Banca** is a modern digital newsstand application that automatically organizes and manages Portuguese newspapers and magazines. With AI-powered categorization and a beautiful, intuitive interface, Banca makes it easy to access and read your favorite publications.

**All-in-one Docker container** - Everything you need in a single, simple deployment!

## What Does "Banca" Mean?

In Portuguese, "banca" means "newsstand" - the traditional street kiosks where people buy newspapers and magazines. Banca brings this familiar concept into the digital age, providing a personal digital newsstand accessible from anywhere.

## Quick Start

```bash
# 1. Start Docker container
./docker-up.sh

# 2. Open your browser
http://localhost

# 3. First time setup:
#    - Create an account
#    - Go to Settings → System & Bot
#    - Add your Gemini API key
#    - Start the bot
```

That's it! No configuration files needed.

## Architecture

Banca runs in a **single Docker container** that includes:
- ✅ React Frontend (Nginx on port 80)
- ✅ FastAPI Backend (internal)
- ✅ Telegram Bot (background process)
- ✅ SQLite Database

**One container. One port. One volume. Simple!**

## Container Architecture

```
┌─────────────────────────────────┐
│         banca:latest            │
│  (Single Container)             │
├─────────────────────────────────┤
│                                 │
│  ┌──────────────────────────┐  │
│  │   Nginx (Frontend)       │  │
│  │   Port 80                │  │
│  └──────────┬───────────────┘  │
│             ↓                   │
│  ┌──────────────────────────┐  │
│  │   FastAPI (Backend)      │  │
│  │   localhost:8000         │  │
│  └──────────────────────────┘  │
│                                 │
│  ┌──────────────────────────┐  │
│  │   Telegram Bot           │  │
│  │   (Background)           │  │
│  └──────────────────────────┘  │
│                                 │
│  ┌──────────────────────────┐  │
│  │   SQLite Database        │  │
│  │   /app/data/             │  │
│  └──────────────────────────┘  │
│                                 │
└─────────────────────────────────┘
         ↓
    ./data (volume)
```

## Key Features

### 📚 **Automatic Organization**
- AI-powered categorization of newspapers and magazines
- Smart file naming and organization
- Automatic thumbnail generation

### 🤖 **Telegram Integration**
- Automatic download from Telegram channels
- Background processing
- Manual review for unknown publications

### 🌐 **Multi-Language Support**
- English 🇬🇧
- Português 🇵🇹
- Español 🇪🇸
- Nederlands 🇳🇱

### 📖 **Beautiful Reading Experience**
- PDF viewer with page navigation
- Reading progress tracking
- Continue reading from where you left off
- Responsive design for all devices

### 🔐 **Secure & Private**
- User authentication
- Admin controls
- Private library management

### 🐳 **Ultra-Simple Deployment**
- Single Docker container
- No environment variables needed
- Configure everything in the UI
- Production-ready

## Technology Stack

- **Frontend**: React + Vite + Nginx
- **Backend**: FastAPI + Python
- **Database**: SQLite
- **PDF Processing**: PDF.js
- **AI**: Google Gemini
- **Telegram**: Pyrogram
- **Deployment**: Docker (all-in-one)

## Project Structure

```
Banca/
├── data/                # Mapped volume (all app data)
│   ├── jornais.db      # Database
│   ├── downloads/      # Downloaded files
│   ├── uploads/        # Uploaded files
│   ├── thumbnails/     # Generated thumbnails
│   └── logs/           # Application logs
├── backend/            # Backend source (not mapped)
├── frontend/           # Frontend source (not mapped)
├── Dockerfile          # All-in-one container
├── docker-compose.yml  # Simple orchestration
├── docker-up.sh        # Start script (with auto-build)
├── dev.sh              # Unified local development script
├── deploy.sh           # Manual deployment script
└── README.md           # This file
```

## Common Commands

```bash
# Start
./docker-up.sh

# Build & Start
./docker-up.sh --build

# Stop
./docker-up.sh --stop
# OR
docker-compose down

# View logs
./docker-up.sh --logs
# OR
docker-compose logs -f

# Local Development (without Docker)
./dev.sh

# Access container
docker exec -it banca bash
```

## Configuration

All configuration is done through the web UI:

1. **Create an account** (first user is automatically admin)
2. **Go to Settings** → System & Bot
3. **Add your Gemini API key**
4. **Start the Telegram bot**

No configuration files needed!

## Data Persistence

All data is stored in `./data/` which is mapped to `/app/data` in the container:
- `jornais.db` - SQLite database
- `downloads/` - Telegram downloads
- `uploads/` - User uploads
- `thumbnails/` - Generated thumbnails
- `logs/` - Application logs

**Backup**: Just backup the `./data/` directory!

## Ports

- **80** - Web interface (Frontend + API)

That's it! Only one port to expose.

## Why One Container?

✅ **Maximum Simplicity** - One image, one container, one command  
✅ **No Configuration** - Everything configured in the UI  
✅ **Portability** - Move it anywhere easily  
✅ **Resource Efficient** - Lower overhead  
✅ **Easy Backup** - Just backup the data folder  
✅ **Perfect for Self-Hosting** - Ideal for personal use  

## Branding

### Logo
📰 Banca

### Tagline
"Your Digital Newsstand"

## Use Cases

- **Personal Library**: Organize your digital newspaper collection
- **Archive Management**: Keep historical editions organized
- **Reading Tracking**: Never lose your place
- **Multi-Device Access**: Read anywhere, anytime
- **Automated Collection**: Set it and forget it with Telegram integration

## Documentation

- `README.md` - This file
- `DOCKER_DEPLOYMENT.md` - Deployment guide
- `DOCKER_OPTIMIZATION.md` - Image optimization details
- `MULTILANGUAGE_SUPPORT.md` - Translation guide

## Troubleshooting

### Container won't start
```bash
docker-compose logs -f
```

### Reset everything
```bash
docker-compose down
rm -rf data/
./docker-start.sh
```

### Rebuild from scratch
```bash
docker-compose down
docker rmi banca:latest
./docker-up.sh --build
```

## License

[Your License Here]

## Support

For issues or questions:
```bash
# Check logs
docker-compose logs -f

# Check status
docker-compose ps

# Verify image
docker images | grep banca
```

---

**Banca** - Everything you need in one simple container 📰

**No config files. No environment variables. Just run it!**
