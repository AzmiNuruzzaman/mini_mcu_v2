# reset.ps1 - Reset Mini-MCU Database Schema
# Run this from the project root: C:\mini-mcu

Write-Host "🚀 Resetting Mini-MCU database schema..." -ForegroundColor Cyan

# Change these if you ever rename your DB or user
$DB_USER = "mini_mcu_user"
$DB_NAME = "mini_mcu"
$SCHEMA_FILE = ".\db\schema.sql"

# Run psql command
psql -U $DB_USER -d $DB_NAME -f $SCHEMA_FILE

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Database reset completed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Database reset failed. Check your schema.sql or connection." -ForegroundColor Red
}
