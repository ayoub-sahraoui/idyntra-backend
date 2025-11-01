# Docker Network Error Fix

## Problem
```
failed to create network: Error response from daemon: failed to check bridge interface existence: numerical result out of range
```

## Root Cause
Docker has exhausted available network subnets or has stale network configurations. This commonly happens when:
1. Too many Docker networks have been created
2. Network cleanup wasn't done properly
3. IP subnet conflicts with existing networks

## Solutions

### Solution 1: Clean Up Unused Networks (Quick Fix)

```powershell
# Stop all containers
docker-compose down

# Remove unused networks
docker network prune -f

# Try again
docker-compose up -d
```

### Solution 2: Remove All Docker Networks

```powershell
# Stop all containers
docker stop $(docker ps -aq)

# Remove all containers
docker rm $(docker ps -aq)

# Remove all networks
docker network prune -f

# Restart Docker daemon
Restart-Service docker

# Start services
docker-compose up -d
```

### Solution 3: Restart Docker Desktop

1. Right-click Docker Desktop icon in system tray
2. Click "Restart"
3. Wait for Docker to restart completely
4. Run `docker-compose up -d`

### Solution 4: Reset Docker Networks

```powershell
# Windows PowerShell (Run as Administrator)
Restart-Service docker

# Or restart Docker Desktop completely
```

### Solution 5: Simplify Network Configuration

If the issue persists, simplify the docker-compose network configuration temporarily.

## Quick Fix Command Sequence

```powershell
# 1. Stop everything
docker-compose down

# 2. Clean networks
docker network prune -f

# 3. List remaining networks (should only see bridge, host, none)
docker network ls

# 4. Restart Docker
Restart-Service docker
# OR restart Docker Desktop

# 5. Try starting again
docker-compose up -d
```

## Prevention

Add to your cleanup routine:
```powershell
# Weekly cleanup
docker system prune -a --volumes -f
```
