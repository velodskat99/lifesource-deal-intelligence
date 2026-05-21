#!/bin/bash
# Install LifeSource launchd agents

set -e

PROJ_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

mkdir -p "$PROJ_DIR/logs"
mkdir -p "$LAUNCH_AGENTS"

# Render plist templates with this checkout's absolute path.
sed "s#__PROJECT_DIR__#$PROJ_DIR#g" \
  "$PROJ_DIR/launchd/com.lifesource.server.plist" \
  > "$LAUNCH_AGENTS/com.lifesource.server.plist"
sed "s#__PROJECT_DIR__#$PROJ_DIR#g" \
  "$PROJ_DIR/launchd/com.lifesource.daily.plist" \
  > "$LAUNCH_AGENTS/com.lifesource.daily.plist"
sed "s#__PROJECT_DIR__#$PROJ_DIR#g" \
  "$PROJ_DIR/launchd/com.lifesource.hmart-weekly-monitor.plist" \
  > "$LAUNCH_AGENTS/com.lifesource.hmart-weekly-monitor.plist"
sed "s#__PROJECT_DIR__#$PROJ_DIR#g" \
  "$PROJ_DIR/launchd/com.lifesource.hmart-weekly-digest.plist" \
  > "$LAUNCH_AGENTS/com.lifesource.hmart-weekly-digest.plist"

# Load agents
launchctl unload "$LAUNCH_AGENTS/com.lifesource.server.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS/com.lifesource.daily.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS/com.lifesource.hmart-weekly-monitor.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS/com.lifesource.hmart-weekly-digest.plist" 2>/dev/null || true
launchctl load "$LAUNCH_AGENTS/com.lifesource.server.plist"
launchctl load "$LAUNCH_AGENTS/com.lifesource.daily.plist"
launchctl load "$LAUNCH_AGENTS/com.lifesource.hmart-weekly-monitor.plist"
launchctl load "$LAUNCH_AGENTS/com.lifesource.hmart-weekly-digest.plist"

echo "LifeSource agents installed and loaded."
echo "  Server: http://localhost:8000"
echo "  Daily job: runs at 8:00 AM"
echo "  H Mart monitor: runs daily at 7:30 AM"
echo "  H Mart planning digest: runs Fridays at 8:30 AM"
