# Game Scheduler

A Discord game scheduling system with microservices architecture, featuring a Discord bot with button interactions, web dashboard with OAuth2 authentication, role-based authorization, multi-channel support, and automated notifications.

## Quick Links by Role

### 👥 For Users

- **[Guild Administrators](docs/GUILD-ADMIN.md)** - Set up the bot in your Discord server, configure permissions, and manage game templates
- **[Game Hosts](docs/HOST-GUIDE.md)** - Create and manage game sessions using the web dashboard
- **[Players](docs/PLAYER-GUIDE.md)** - Join games, receive notifications, and manage your calendar

### 💻 For Contributors

- **[Developer Documentation](docs/developer/README.md)** - Development setup, architecture, testing, and contributing guidelines
- **[Deployment Documentation](docs/deployment/README.md)** - Self-hosting, configuration, and production deployment

## What is Game Scheduler?

Game Scheduler helps Discord communities organize gaming sessions through:

- **Discord Bot** - Post game announcements to channels, collect signups via buttons, send reminder DMs
- **Web Dashboard** - OAuth-authenticated interface for creating and managing games
- **Automated Notifications** - Database-driven scheduler sends reminders before games start
- **Waitlist Management** - Automatic participant promotion when spots become available
- **Calendar Integration** - Download game sessions as .ics files for personal calendars

## Key Features

- Discord button interactions for joining/leaving games
- Role-based permissions with guild-specific bot manager roles
- Multi-channel support with template-based game creation
- Display name resolution (uses Discord nicknames)
- Microservices architecture with FastAPI, discord.py, RabbitMQ, and PostgreSQL

## License

Copyright 2025-2026 Bret McKee (bret.mckee@gmail.com)

Game Scheduler is available as open source software under the MIT License.
See COPYING.txt for the full license text.

Please contact the author if you are interested in obtaining it under other
terms.
