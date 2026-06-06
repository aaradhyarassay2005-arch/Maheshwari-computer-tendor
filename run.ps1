# Tender Intelligence Platform - Windows Start Utility
# Automatically configures local PostgreSQL container, runs migrations, launches Backend & Frontend.

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  TENDER INTELLIGENCE PLATFORM LAUNCHER       " -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Check Docker Status
Write-Host "`n[1/5] Checking Docker daemon status..." -ForegroundColor Yellow
$DockerInstalled = $true
$DockerRunning = $true

Get-Command docker -ErrorAction SilentlyContinue >$null
if ($LastExitCode -ne 0 -and -not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $DockerInstalled = $false
    Write-Host "[WARNING] docker command not found. Docker Desktop might not be installed or not in PATH." -ForegroundColor Yellow
} else {
    docker ps >$null 2>&1
    if ($LastExitCode -ne 0) {
        $DockerRunning = $false
        Write-Host "[WARNING] Docker daemon is not running. Please make sure Docker Desktop is started." -ForegroundColor Yellow
    }
}

if (-not $DockerInstalled -or -not $DockerRunning) {
    Write-Host "`n[!] Docker database services cannot be auto-started." -ForegroundColor Red
    Write-Host "Trying to bootstrap the local PostgreSQL database on port 5432..." -ForegroundColor Yellow

    $PsqlPath = (Get-Command psql -ErrorAction SilentlyContinue).Source
    if (-not $PsqlPath) {
        Write-Host "[ERROR] psql command not found. Please start PostgreSQL manually or install the PostgreSQL client tools." -ForegroundColor Red
    } else {
        $env:PGPASSWORD = "postgres"
        $DbExists = & $PsqlPath -h localhost -p 5432 -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='tender_db';" 2>$null
        if ($DbExists -notmatch '1') {
            Write-Host "[INFO] Creating database tender_db..." -ForegroundColor Yellow
            & $PsqlPath -h localhost -p 5432 -U postgres -d postgres -c "CREATE DATABASE tender_db;"
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[ERROR] Failed to create tender_db. Make sure PostgreSQL is running and credentials are correct." -ForegroundColor Red
            } else {
                Write-Host "[SUCCESS] Database tender_db is ready." -ForegroundColor Green
            }
        } else {
            Write-Host "[SUCCESS] Database tender_db already exists." -ForegroundColor Green
        }
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
} else {
    # Spin Up Local PostgreSQL Container
    Write-Host "`n[2/5] Starting local PostgreSQL database via Docker..." -ForegroundColor Yellow
    docker-compose up -d db
    if ($LastExitCode -ne 0) {
        Write-Host "[WARNING] Failed to launch PostgreSQL container via docker-compose." -ForegroundColor Yellow
    } else {
        Write-Host "[SUCCESS] Database container started." -ForegroundColor Green
    }
    # Wait for database health check
    Write-Host "Waiting for database to accept connections..." -ForegroundColor Yellow
    Start-Sleep -Seconds 4
}

# 2. Check Python Status
Write-Host "`n[3/5] Setting up Python Backend environment..." -ForegroundColor Yellow
Get-Command python -ErrorAction SilentlyContinue >$null
$PythonInstalled = $?
if (-not $PythonInstalled) {
    Write-Host "[ERROR] python command not found. Please install Python 3.10+." -ForegroundColor Red
} else {
    if (-not (Test-Path "backend\.venv")) {
        Write-Host "Virtual environment not found. Creating backend\.venv..." -ForegroundColor Yellow
        Start-Process powershell -Wait -ArgumentList "-Command `\"cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements.txt`\""
    } else {
        Write-Host "Backend virtual environment verified. Syncing packages..." -ForegroundColor Yellow
        Start-Process powershell -Wait -ArgumentList "-Command `\"cd backend; .venv\Scripts\pip install -r requirements.txt`\""
    }

    Write-Host "Running Alembic database migrations..." -ForegroundColor Yellow
    Start-Process powershell -Wait -ArgumentList "-Command `\"cd backend; .venv\Scripts\alembic upgrade head`\""
    if ($LastExitCode -ne 0) {
        Write-Host "[WARNING] Migrations completed with non-zero exit code. If this is a new database, make sure it is initialized." -ForegroundColor Yellow
    } else {
        Write-Host "[SUCCESS] Database migrations complete." -ForegroundColor Green
    }

    # Spawning Backend Uvicorn Server in background
    Write-Host "Spawning FastAPI Backend server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit -Command `\"cd backend; .venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`\"" -Title "FastAPI Backend Server"
}

# 3. Check Node.js Status
Write-Host "`n[4/5] Setting up Next.js Frontend environment..." -ForegroundColor Yellow
Get-Command npm -ErrorAction SilentlyContinue >$null
$NpmInstalled = $?
if (-not $NpmInstalled) {
    Write-Host "[ERROR] npm command not found. Please install Node.js." -ForegroundColor Red
} else {
    if (-not (Test-Path "frontend\node_modules")) {
        Write-Host "Node modules not found. Running npm install..." -ForegroundColor Yellow
        Start-Process powershell -Wait -ArgumentList "-Command `\"cd frontend; npm install`\""
    }

    # Spawning Frontend Next.js Server in background
    Write-Host "Spawning Next.js Frontend developer server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit -Command `\"cd frontend; npm run dev`\"" -Title "Next.js Frontend Developer Server"
}

# 4. Finish
Write-Host "`n==============================================" -ForegroundColor Green
Write-Host "  ALL SERVICES INITIATED!                     " -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  - Next.js Client: http://localhost:3000" -ForegroundColor Cyan
Write-Host "  - FastAPI Swagger Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Green
Write-Host "Launching local application in default browser..." -ForegroundColor Yellow

Start-Sleep -Seconds 3
Start-Process "http://localhost:3000"
