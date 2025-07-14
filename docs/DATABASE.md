# Database Schema

## Overview

Database: [PostgreSQL/MySQL/MongoDB]

### PostgreSQL MCP Configuration

When using PostgreSQL with Claude's MCP (Model Context Protocol), the configuration is set up in `~/.config/claude/claude_desktop_config.json`.

To connect to different databases (like `uganomics` or `posse_rewards`), modify the connection URL and PGDATABASE environment variable accordingly:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://postgres:postgres@localhost:5432/your_database_name"
      ],
      "env": {
        "PGDATABASE": "your_database_name"
      }
    }
  }
}
```

Replace `your_database_name` with the actual database you want to connect to (e.g., `uganomics`, `posse_rewards`, etc.).

## Tables/Collections

### users
- `id` (primary key)
- `email` (unique)
- `name`
- `created_at`
- `updated_at`

### [table_name]
- `id` (primary key)
- `user_id` (foreign key)
- `[fields]`

## Relationships

- User has many [Resources]
- [Define other relationships]

## Indexes

- `users.email` - For login queries
- `[table.field]` - [Reason]

## Migrations

Run migrations:
```bash
npm run migrate
```

---
Last updated: [Date]