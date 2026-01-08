# MEGA-AI - Product Requirements Document

## Overview

**MEGA-AI** - bu AI-powered data transformation tool bo'lib, u codebase ni o'rganib, kerakli o'zgarishlarni avtomatik amalga oshiradi. Asosiy maqsad - takroriy integration ishlarini avtomatlashtirish.

**Asosiy g'oya**: AI yordamida AI agent yaratish. Orchestrator AI loyihani o'rganadi va Worker AI uchun maxsus script generatsiya qiladi.

---

## Core Concepts

### Two-Stage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: ORCHESTRATOR                                          │
│  Model: Claude Opus / GPT-5.2 (aqlli, analiz uchun)            │
│                                                                 │
│  • Codebase analysis                                            │
│  • Strategy planning                                            │
│  • Script generation (backup.py, runner.py)                    │
│  • Worker AI uchun system prompt tayyorlash                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 2: WORKER                                                │
│  Model: Claude Sonnet / GPT-4o-mini (tez, arzon)               │
│                                                                 │
│  • Generated script ishga tushirish                            │
│  • Data transformation                                          │
│  • Real-time progress                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **AI decides everything** - Framework, DB type, backup strategy - barchasini AI o'zi aniqlaydi
2. **Human confirms** - Har qanday o'zgarishdan oldin user tasdiqlaydi
3. **Safe by default** - Dry-run, backup, rollback har doim mavjud
4. **Open source** - Community driven development

---

## CLI Commands

### `mega-ai init`

Birinchi marta setup qilish.

```bash
$ mega-ai init

Welcome to MEGA-AI! 🚀

Select AI provider:
  1. Anthropic (Claude)
  2. OpenAI (GPT)
  3. Both
> 1

Enter Anthropic API key: sk-ant-xxxxx

Select orchestrator model (for analysis & planning):
  1. claude-opus-4-20250514 (recommended)
  2. claude-sonnet-4-20250514
> 1

Select worker model (for data transformation):
  1. claude-sonnet-4-20250514 (recommended)
  2. claude-haiku-3-5-20241022 (faster, cheaper)
> 1

✅ Configuration saved to ~/.mega-ai/config.yaml
```

**Output**: `~/.mega-ai/config.yaml`

```yaml
providers:
  anthropic:
    api_key: "sk-ant-xxxxx"

models:
  orchestrator: "claude-opus-4-20250514"
  worker: "claude-sonnet-4-20250514"
```

---

### `mega-ai run "<task>"`

Orchestrator AI ni ishga tushiradi. Codebase ni o'rganadi va task uchun scriptlar generatsiya qiladi.

```bash
$ mega-ai run "product titlelarni title case qil, masalan SANDISK ULTRA -> SanDisk Ultra"

🤖 Orchestrator AI started...

🔍 Analyzing project...
   $ ls -la
   $ cat composer.json
   ✓ Framework: Laravel 10.x

   $ cat .env | grep DB_
   $ cat config/database.php
   ✓ Database: MySQL 8.0 @ localhost

   $ find app/Models -name "*.php"
   $ cat app/Models/Product.php
   ✓ Model: Product (table: products)

   $ php artisan tinker --execute="Product::take(5)->pluck('title')"
   ✓ Sample data retrieved

📋 Analysis complete:
   ├── Target: products.title
   ├── Rows: 1,247
   ├── Backup: mysqldump (products table)
   └── Transform: Title case with brand recognition

📝 Generating scripts...
   ├── .mega-ai/tasks/a1b2c3d4/backup.py
   ├── .mega-ai/tasks/a1b2c3d4/runner.py
   └── .mega-ai/tasks/a1b2c3d4/config.json

✅ Task ready!

To preview (dry-run):
  mega-ai worker a1b2c3d4 --dry-run

To execute:
  mega-ai worker a1b2c3d4
```

---

### `mega-ai worker <uuid> [--dry-run]`

Worker AI ni ishga tushiradi. Generated scriptlarni execute qiladi.

#### Dry-run mode:

```bash
$ mega-ai worker a1b2c3d4 --dry-run

🔍 Loading task a1b2c3d4...
📦 Backup: SKIPPED (dry-run mode)

🚀 Running transformation (DRY-RUN)...

┌─────────────────────────────────────────────────────────────────┐
│ Preview - First 10 items                                        │
├─────────────────────────────────────────────────────────────────┤
│ BEFORE                          │ AFTER                         │
├─────────────────────────────────┼───────────────────────────────┤
│ SANDISK ULTRA USB 3.0 128GB    │ SanDisk Ultra USB 3.0 128GB  │
│ KINGSTON DATATRAVELER 64GB     │ Kingston DataTraveler 64GB   │
│ SAMSUNG EVO PLUS 256GB         │ Samsung EVO Plus 256GB       │
│ LOGITECH MX MASTER 3           │ Logitech MX Master 3         │
│ APPLE AIRPODS PRO 2ND GEN      │ Apple AirPods Pro 2nd Gen    │
│ WD BLACK SN850X 1TB            │ WD Black SN850X 1TB          │
│ CORSAIR VENGEANCE RGB 32GB     │ Corsair Vengeance RGB 32GB   │
│ ASUS ROG STRIX RTX 4080        │ ASUS ROG Strix RTX 4080      │
│ RAZER DEATHADDER V3 PRO        │ Razer DeathAdder V3 Pro      │
│ STEELSERIES ARCTIS NOVA PRO    │ SteelSeries Arctis Nova Pro  │
└─────────────────────────────────┴───────────────────────────────┘

📊 Summary:
   ├── Total rows: 1,247
   ├── Would transform: 1,198
   ├── Already correct: 49
   └── Estimated time: ~2 minutes

To execute for real:
  mega-ai worker a1b2c3d4
```

#### Execute mode:

```bash
$ mega-ai worker a1b2c3d4

🔍 Loading task a1b2c3d4...

📦 Creating backup...
   $ mysqldump -u root mydb products > backup_20240108_123045.sql
   ✓ Backup saved: .mega-ai/tasks/a1b2c3d4/backups/backup_20240108_123045.sql

⚠️  This will modify 1,247 rows in 'products' table.
   Proceed? [y/N] y

🚀 Running transformation...
   [████████████████████████████████████████] 100% (1247/1247)

   ├── Transformed: 1,198
   ├── Skipped (already correct): 49
   ├── Errors: 3 (logged to errors.log)
   └── Time: 1m 47s

✅ Transformation complete!

To rollback:
  mega-ai rollback a1b2c3d4
```

---

### `mega-ai rollback <uuid>`

O'zgarishlarni qaytarish.

```bash
$ mega-ai rollback a1b2c3d4

🔍 Loading task a1b2c3d4...
📦 Found backup: backup_20240108_123045.sql

⚠️  This will restore 'products' table to previous state.
   Proceed? [y/N] y

🔄 Restoring...
   $ mysql -u root mydb < backup_20240108_123045.sql
   ✓ Restored successfully

✅ Rollback complete!
```

---

### `mega-ai history`

O'tgan tasklar ro'yxati.

```bash
$ mega-ai history

┌──────────┬─────────────────────────────────┬─────────────┬───────────┐
│ UUID     │ Description                      │ Date        │ Status    │
├──────────┼─────────────────────────────────┼─────────────┼───────────┤
│ a1b2c3d4 │ product titlelarni title case   │ 2024-01-08  │ completed │
│ e5f6g7h8 │ user emaillarni lowercase       │ 2024-01-07  │ completed │
│ i9j0k1l2 │ category nomlarini capitalize   │ 2024-01-05  │ rolled_back│
└──────────┴─────────────────────────────────┴─────────────┴───────────┘
```

---

## Orchestrator AI

### Function Calling Tools

Orchestrator AI quyidagi tools bilan ishlaydi:

```python
tools = [
    {
        "name": "run_command",
        "description": "Run shell command in project directory. Use for: ls, cat, grep, find, head, tail, wc, etc.",
        "parameters": {
            "command": {
                "type": "string",
                "description": "Shell command to execute"
            }
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file",
        "parameters": {
            "path": {
                "type": "string",
                "description": "File path relative to .mega-ai/tasks/{uuid}/"
            },
            "content": {
                "type": "string",
                "description": "File content"
            }
        }
    },
    {
        "name": "ask_user",
        "description": "Ask user for clarification when task is ambiguous",
        "parameters": {
            "question": {
                "type": "string",
                "description": "Question to ask"
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: multiple choice options"
            }
        }
    },
    {
        "name": "complete_task",
        "description": "Mark task as ready for worker execution",
        "parameters": {
            "summary": {
                "type": "string",
                "description": "Summary of what was generated"
            }
        }
    }
]
```

### System Prompt (Orchestrator)

```
You are MEGA-AI Orchestrator - an AI that analyzes codebases and generates data transformation scripts.

## Your Goal
Given a user's task description, you need to:
1. Analyze the project structure and find relevant files
2. Understand the database schema and connections
3. Generate backup.py and runner.py scripts
4. Generate appropriate system prompt for Worker AI

## Available Tools
- run_command: Execute shell commands (cat, grep, find, ls, etc.)
- write_file: Write generated scripts
- ask_user: Ask for clarification if task is ambiguous
- complete_task: Mark task as ready

## Analysis Strategy
1. First, understand the project:
   - ls, cat package.json/composer.json/requirements.txt
   - Identify framework (Laravel, Django, FastAPI, Express, etc.)

2. Find database configuration:
   - .env files
   - config files
   - Connection strings

3. Find relevant models/schemas:
   - Model files
   - Migration files
   - Schema definitions

4. Get sample data:
   - Use framework's REPL (tinker, shell, etc.)
   - Or direct DB query

5. Generate scripts:
   - backup.py: backup() and restore() functions
   - runner.py: main transformation logic with Worker AI integration

## Important Rules
- NEVER execute destructive commands (DROP, DELETE, UPDATE, etc.)
- Always use read-only commands for analysis
- If unsure, ask_user for clarification
- Generated runner.py must include proper error handling and logging
```

---

## Worker AI

### Generated runner.py Structure

```python
#!/usr/bin/env python3
"""
Generated by MEGA-AI Orchestrator
Task: product titlelarni title case qil
UUID: a1b2c3d4
"""

import os
import json
import mysql.connector
from anthropic import Anthropic

# Configuration
CONFIG = {
    "db": {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "myshop"
    },
    "target": {
        "table": "products",
        "column": "title",
        "primary_key": "id"
    },
    "ai": {
        "model": "claude-sonnet-4-20250514",
        "batch_size": "dynamic",  # Token-based batching
        "max_tokens_per_batch": 4000
    }
}

WORKER_SYSTEM_PROMPT = """
You are a product title transformer. Your job is to convert UPPERCASE product titles to proper Title Case.

## Rules
1. Brand names should be properly capitalized:
   - SANDISK → SanDisk
   - KINGSTON → Kingston
   - LOGITECH → Logitech
   - ASUS → ASUS (stays uppercase - it's an acronym)

2. Technical terms stay uppercase:
   - USB, SSD, HDD, GB, TB, RAM, DDR, RGB, RTX, etc.

3. Model numbers stay as-is:
   - RTX 4080, MX Master 3, etc.

4. Common words become lowercase:
   - FOR, WITH, AND, THE, etc. (unless first word)

## Input Format
JSON array of objects: [{"id": 1, "title": "ORIGINAL TITLE"}, ...]

## Output Format
JSON array of objects: [{"id": 1, "title": "Transformed Title"}, ...]

IMPORTANT: Return ONLY valid JSON, no explanations.
"""

def get_db_connection():
    return mysql.connector.connect(**CONFIG["db"])

def fetch_items(conn, limit=None, offset=0):
    cursor = conn.cursor(dictionary=True)
    query = f"""
        SELECT {CONFIG["target"]["primary_key"]}, {CONFIG["target"]["column"]}
        FROM {CONFIG["target"]["table"]}
    """
    if limit:
        query += f" LIMIT {limit} OFFSET {offset}"
    cursor.execute(query)
    return cursor.fetchall()

def transform_batch(client, items):
    """Send batch to Worker AI for transformation"""
    response = client.messages.create(
        model=CONFIG["ai"]["model"],
        max_tokens=4096,
        system=WORKER_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Transform these titles:\n{json.dumps(items, ensure_ascii=False)}"
        }]
    )
    
    result_text = response.content[0].text
    return json.loads(result_text)

def update_item(conn, item_id, new_value):
    """Update single item in database"""
    cursor = conn.cursor()
    query = f"""
        UPDATE {CONFIG["target"]["table"]}
        SET {CONFIG["target"]["column"]} = %s
        WHERE {CONFIG["target"]["primary_key"]} = %s
    """
    cursor.execute(query, (new_value, item_id))
    conn.commit()

def create_dynamic_batches(items, max_tokens=4000):
    """Create batches based on estimated token count"""
    batches = []
    current_batch = []
    current_tokens = 0
    
    for item in items:
        # Rough estimate: 1 token ≈ 4 characters
        item_tokens = len(str(item)) // 4 + 10
        
        if current_tokens + item_tokens > max_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        
        current_batch.append(item)
        current_tokens += item_tokens
    
    if current_batch:
        batches.append(current_batch)
    
    return batches

def run(dry_run=False):
    """Main execution function"""
    client = Anthropic()
    conn = get_db_connection()
    
    # Fetch all items
    items = fetch_items(conn)
    total = len(items)
    
    print(f"📊 Found {total} items to process")
    
    # Create dynamic batches
    batches = create_dynamic_batches(items)
    print(f"📦 Created {len(batches)} batches")
    
    transformed = 0
    skipped = 0
    errors = []
    
    for i, batch in enumerate(batches):
        print(f"\r🔄 Processing batch {i+1}/{len(batches)}...", end="")
        
        try:
            results = transform_batch(client, batch)
            
            for original, result in zip(batch, results):
                if original["title"] == result["title"]:
                    skipped += 1
                    continue
                
                if dry_run:
                    print(f"\n  {original['title']} → {result['title']}")
                else:
                    try:
                        update_item(conn, result["id"], result["title"])
                        transformed += 1
                    except Exception as e:
                        errors.append({"id": result["id"], "error": str(e)})
                        
        except Exception as e:
            # Log batch error and continue
            for item in batch:
                errors.append({"id": item["id"], "error": str(e)})
    
    print(f"\n\n✅ Complete!")
    print(f"   Transformed: {transformed}")
    print(f"   Skipped: {skipped}")
    print(f"   Errors: {len(errors)}")
    
    if errors:
        with open("errors.log", "w") as f:
            json.dump(errors, f, indent=2)
        print(f"   Error log: errors.log")
    
    conn.close()

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    run(dry_run=dry_run)
```

---

## Generated backup.py Structure

```python
#!/usr/bin/env python3
"""
Generated by MEGA-AI Orchestrator
Task: product titlelarni title case qil
UUID: a1b2c3d4
"""

import os
import subprocess
from datetime import datetime

CONFIG = {
    "db": {
        "type": "mysql",
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "myshop"
    },
    "target": {
        "table": "products"
    }
}

BACKUP_DIR = os.path.join(os.path.dirname(__file__), "backups")

def backup():
    """Create backup of target table"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.sql"
    filepath = os.path.join(BACKUP_DIR, filename)
    
    if CONFIG["db"]["type"] == "mysql":
        cmd = [
            "mysqldump",
            "-h", CONFIG["db"]["host"],
            "-u", CONFIG["db"]["user"],
            CONFIG["db"]["database"],
            CONFIG["target"]["table"]
        ]
        if CONFIG["db"]["password"]:
            cmd.extend([f"-p{CONFIG['db']['password']}"])
        
        with open(filepath, "w") as f:
            subprocess.run(cmd, stdout=f, check=True)
    
    print(f"✅ Backup created: {filepath}")
    return filepath

def restore(backup_file=None):
    """Restore from backup"""
    if backup_file is None:
        # Find latest backup
        backups = sorted(os.listdir(BACKUP_DIR), reverse=True)
        if not backups:
            print("❌ No backups found")
            return False
        backup_file = os.path.join(BACKUP_DIR, backups[0])
    
    if CONFIG["db"]["type"] == "mysql":
        cmd = [
            "mysql",
            "-h", CONFIG["db"]["host"],
            "-u", CONFIG["db"]["user"],
            CONFIG["db"]["database"]
        ]
        if CONFIG["db"]["password"]:
            cmd.extend([f"-p{CONFIG['db']['password']}"])
        
        with open(backup_file, "r") as f:
            subprocess.run(cmd, stdin=f, check=True)
    
    print(f"✅ Restored from: {backup_file}")
    return True

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        backup_file = sys.argv[2] if len(sys.argv) > 2 else None
        restore(backup_file)
    else:
        backup()
```

---

## Task Folder Structure

```
.mega-ai/
└── tasks/
    └── a1b2c3d4/
        ├── config.json         # Task metadata
        ├── backup.py           # Backup/restore script  
        ├── runner.py           # Worker script
        ├── backups/            # Backup files
        │   └── backup_20240108_123045.sql
        └── logs/
            ├── orchestrator.log    # AI analysis log
            ├── run.log             # Execution log
            └── errors.log          # Error log
```

### config.json

```json
{
    "uuid": "a1b2c3d4",
    "created_at": "2024-01-08T12:30:00Z",
    "description": "product titlelarni title case qil",
    "status": "pending",
    
    "project": {
        "path": "/home/user/myshop",
        "framework": "laravel",
        "framework_version": "10.x"
    },
    
    "database": {
        "type": "mysql",
        "version": "8.0",
        "host": "localhost",
        "name": "myshop"
    },
    
    "target": {
        "type": "database",
        "table": "products",
        "column": "title",
        "primary_key": "id",
        "rows_count": 1247
    },
    
    "models": {
        "orchestrator": "claude-opus-4-20250514",
        "worker": "claude-sonnet-4-20250514"
    },
    
    "execution": {
        "batch_strategy": "dynamic",
        "max_tokens_per_batch": 4000,
        "estimated_cost": 0.12,
        "estimated_time": "2 minutes"
    }
}
```

---

## Interactive Mode (Clarification)

Agar task noaniq bo'lsa, Orchestrator AI `ask_user` tool ishlatadi:

```bash
$ mega-ai run "emaillarni lowercase qil"

🤖 Orchestrator AI started...

🔍 Analyzing project...
   ✓ Framework: Laravel 10.x
   ✓ Database: MySQL 8.0

❓ Clarification needed:
   
   Found multiple tables with email columns:
   
   1. users.email (5,234 rows)
   2. customers.email (12,456 rows)  
   3. newsletter_subscribers.email (3,789 rows)
   
   Which one(s) should I transform?
   
   > 1,2
   
   ✓ Selected: users.email, customers.email

📋 Analysis complete...
```

---

## Error Handling Strategy

### During Analysis (Stage 1)
```
❌ Xato: DB ga ulanib bo'lmadi
   → Orchestrator to'xtaydi
   → User ga xabar beradi
   → Fix qilishni so'raydi
```

### During Execution (Stage 2)

| Error Type | Action |
|------------|--------|
| Connection error | Stop + prompt rollback |
| Update error (single row) | Log + continue |
| AI response parse error | Log + retry 1x, then continue |
| AI rate limit | Wait + retry |
| Batch error | Log all items + continue |
| Unknown error | Stop + prompt rollback |

---

## Supported Frameworks & Databases

### Phase 1 (MVP)
- **Frameworks**: Laravel, Django, FastAPI, Express.js
- **Databases**: MySQL, PostgreSQL, MongoDB
- **File types**: JSON, YAML

### Phase 2
- **Frameworks**: Rails, Spring Boot, NestJS
- **Databases**: SQLite, Redis
- **File types**: XML, CSV, .env

### Phase 3
- **APIs**: REST endpoints transformation
- **Cloud DBs**: Supabase, PlanetScale, MongoDB Atlas

---

## Security Considerations

1. **API Keys**
   - Stored in `~/.mega-ai/config.yaml`
   - File permissions: 600 (owner only)
   - Never logged or displayed

2. **Database Credentials**
   - Read from project's existing config files
   - Never stored in mega-ai config
   - Prompted if not found

3. **Command Execution**
   - Orchestrator: Read-only commands only
   - Blocklist: `rm`, `drop`, `delete`, `truncate`, etc.
   - All commands logged

4. **Backup**
   - Required before any modification
   - Stored locally in task folder
   - User responsible for remote backup

---

## Future Considerations

1. **Parallel Execution**
   - Multiple worker processes
   - Faster for large datasets

2. **Resumable Tasks**
   - Continue from where it stopped
   - Useful for very large transformations

3. **Team Features**
   - Share task templates
   - Approval workflow

4. **Web UI**
   - Visual task builder
   - Real-time monitoring dashboard

5. **Plugins**
   - Custom analyzers
   - Custom transformers
   - Community contributions

---

## Open Source Plan

**License**: MIT

**Repository Structure**:
```
mega-ai/
├── src/
│   ├── cli/           # CLI commands
│   ├── orchestrator/  # Orchestrator AI logic
│   ├── worker/        # Worker execution engine
│   ├── analyzers/     # Framework/DB analyzers
│   └── utils/         # Helpers
├── tests/
├── docs/
├── examples/
├── README.md
├── pyproject.toml
└── LICENSE
```

**Contribution Guidelines**:
- New analyzer support
- New database connectors
- Bug fixes
- Documentation

---

## Success Metrics

1. **Time saved**: 80% reduction in integration time
2. **Accuracy**: 95%+ transformation accuracy
3. **Adoption**: GitHub stars, forks, contributors
4. **Coverage**: Support for top 10 frameworks/databases

---

## Summary

MEGA-AI is a two-stage AI-powered tool:

1. **Orchestrator** (smart model) - analyzes codebase, generates scripts
2. **Worker** (fast model) - executes transformations

Key features:
- Framework/DB auto-detection
- Interactive clarification
- Dry-run preview
- Automatic backup/rollback
- Real-time progress
- Error handling with continuation

Target users:
- Developers with repetitive data transformation tasks
- Teams managing multiple projects
- Anyone needing safe, AI-powered data modifications
