# Nexus AI

Welcome to the Nexus AI project repository.

## Tech Stack

*   **Backend:** FastAPI, Python 3.12, uv, SQLAlchemy 2.0 (async), Alembic
*   **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Zustand
*   **Databases:** PostgreSQL (Relational), Redis (Cache/State), Qdrant (Vectors)
*   **Workflow Engine:** n8n

## Quick Start

### 1. Prerequisites
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- N8N Instance (Local or Cloud)

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
# source venv/bin/activate

pip install -r requirements.txt

# Create your environment file and fill in API keys
cp .env.example .env

# Start the required databases (Postgres, Redis, Qdrant)
docker-compose up -d

# Run migrations and start the server
alembic upgrade head
uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Database Migrations

The backend uses SQLAlchemy 2.0 with asynchronous drivers (`asyncpg`) and Alembic for migrations.

To generate a new migration after modifying models:
```bash
cd backend
alembic revision --autogenerate -m "description of changes"
```

To apply migrations to the database:
```bash
cd backend
alembic upgrade head
```

## Repository Structure

The project is organized as follows:

- **[.github/](file:///d:/Nexus-AI/.github/)**: GitHub actions, workflows, and templates.
- **[backend/](file:///d:/Nexus-AI/backend/)**: Backend application source code.
- **[database/](file:///d:/Nexus-AI/database/)**: Database schemas, migrations, and seed scripts.
- **[docker/](file:///d:/Nexus-AI/docker/)**: Docker configuration files and scripts.
- **[docs/](file:///d:/Nexus-AI/docs/)**: Project documentation and architecture details.
- **[frontend/](file:///d:/Nexus-AI/frontend/)**: Frontend client source code.
- **[n8n/](file:///d:/Nexus-AI/n8n/)**: n8n workflows and configurations.
- **[tests/](file:///d:/Nexus-AI/tests/)**: Automated integration and unit tests.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

### Running the Project

To launch the full suite of services, run:

```bash
docker-compose up -d
```
