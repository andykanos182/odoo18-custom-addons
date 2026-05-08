# 🔗 MCP (Model Context Protocol) Integration Handoff

**Gopokaja Odoo 18 - Linux Server Direct Access**

---

## 📋 DOCUMENT PURPOSE

Handoff ini untuk **setup & troubleshooting MCP integration** dengan Odoo 18 Linux server di `192.168.1.47:/opt/odoo18`.

**Tujuan:** Claude bisa akses server **secara langsung** untuk:
- ✅ Read/write files di `/opt/odoo18/`
- ✅ Execute Docker commands
- ✅ Query PostgreSQL database
- ✅ Monitor logs real-time
- ✅ Diagnose & fix errors langsung

---

## 🎯 QUICK START

### **Setup MCP di Claude Chat (First Time):**

1. **Open Claude Chat** → Chat settings
2. **Find "Connected Tools"** atau **"MCP Servers"**
3. **Add New MCP Server:**
   - Server: `192.168.1.47`
   - Username: `root`
   - SSH Key or Password
   - Port: `22`
4. **Test Connection:**
   ```
   Claude: "Test connection, jalankan: docker ps"
   ```

---

## 📊 SERVER INFORMATION

| Item | Value |
|------|-------|
| **Server IP** | `192.168.1.47` |
| **Project Path** | `/opt/odoo18/` |
| **SSH Port** | 22 |
| **Odoo Port** | 8018 |
| **DB Port** | 5433 |

---

## 🔑 CREDENTIALS

```
Server: 192.168.1.47
User: root
Port: 22

Database User: andyka
Database Password: andykanos182

Odoo Admin: admin
Odoo Master Password: themasterodoo18
```

---

## 🗂️ FOLDER STRUCTURE

```
/opt/odoo18/
├── docker-compose.yaml
├── .env
├── odoo.conf
├── Odoo_data/
├── Postgres17_Odoo18/
├── Addons/
├── logs/
└── backups/
```

---

## 🚀 COMMON MCP COMMANDS

### **Container Management**

```bash
# Check all containers
docker ps -a

# View Odoo logs
docker logs Odoo18 --tail 100

# View PostgreSQL logs
docker logs Postgres17-Odoo18 --tail 50

# Restart specific container
docker compose restart Odoo18

# Stop container
docker compose stop Odoo18

# Start container
docker compose up -d Odoo18

# View live logs
docker logs Odoo18 -f
```

---

### **File Operations**

```bash
# List files
ls -la /opt/odoo18/

# View file content
cat /opt/odoo18/odoo.conf

# Edit file
nano /opt/odoo18/odoo.conf

# Check permissions
ls -la /opt/odoo18/Odoo_data/

# Fix permissions
chmod -R 777 /opt/odoo18/Odoo_data
chown -R 101:101 /opt/odoo18/Odoo_data

# Backup file
cp /opt/odoo18/odoo.conf /opt/odoo18/odoo.conf.backup
```

---

### **Database Operations**

```bash
# Connect to PostgreSQL
docker exec -it Postgres17-Odoo18 psql -U postgres

# List databases
docker exec -it Postgres17-Odoo18 psql -U postgres -l

# List users
docker exec -it Postgres17-Odoo18 psql -U postgres -c "\du"

# Test user connection
docker exec -it Postgres17-Odoo18 psql -U andyka -c "SELECT 1"

# Backup database
docker exec Postgres17-Odoo18 pg_dump -U postgres gopokaja > /opt/odoo18/backups/gopokaja_backup.sql
```

---

### **Module Operations**

```bash
# Upgrade specific module
docker exec -it Odoo18 odoo --config=/etc/odoo/odoo.conf -d gopokaja -u module_name --stop-after-init

# Upgrade all modules
docker exec -it Odoo18 odoo --config=/etc/odoo/odoo.conf -d gopokaja --upgrade=all --stop-after-init

# Check Odoo version
docker exec Odoo18 odoo --version
```

---

### **System Info**

```bash
# Disk space
df -h /opt/odoo18

# Memory usage
free -h

# Running processes
ps aux | grep odoo

# File descriptor limit
ulimit -n

# Network connections
netstat -tuln | grep 8018
```

---

## 🐛 TROUBLESHOOTING

### **Problem 1: Internal Server Error 500**

**Diagnosis:**
```bash
docker logs Odoo18 --tail 100
ls -la /opt/odoo18/Odoo_data/
docker logs Postgres17-Odoo18 --tail 50
```

**Fix:**
```bash
chmod -R 777 /opt/odoo18/Odoo_data
chown -R 101:101 /opt/odoo18/Odoo_data
docker compose restart Odoo18
```

---

### **Problem 2: Container Not Starting**

**Diagnosis:**
```bash
docker ps -a
docker logs [CONTAINER_NAME] --tail 100
docker compose config
```

**Fix:**
```bash
docker compose down
docker compose up -d
```

---

### **Problem 3: Database Connection Failed**

**Diagnosis:**
```bash
docker logs Postgres17-Odoo18 --tail 100
docker exec -it Postgres17-Odoo18 psql -U andyka -c "SELECT 1"
docker exec -it Postgres17-Odoo18 psql -U postgres -c "\du"
```

**Fix:**
```bash
grep db_password /opt/odoo18/odoo.conf
docker compose restart Postgres17-18
```

---

### **Problem 4: Module Installation Error**

**Diagnosis:**
```bash
ls -la /opt/odoo18/Addons/ | grep module_name
cat /opt/odoo18/Addons/module_name/__manifest__.py
docker logs Odoo18 -f
```

**Fix:**
```bash
docker exec -it Odoo18 odoo --config=/etc/odoo/odoo.conf -d gopokaja -u module_name --stop-after-init
docker compose restart Odoo18
```

---

### **Problem 5: Permission Denied Error**

**Diagnosis:**
```bash
ls -la /opt/odoo18/Odoo_data/
```

**Fix:**
```bash
chmod -R 777 /opt/odoo18/Odoo_data
chown -R 101:101 /opt/odoo18/Odoo_data
ls -la /opt/odoo18/Odoo_data/
docker compose restart Odoo18
```

---

### **Problem 6: Cloudflare Tunnel Not Working**

**Diagnosis:**
```bash
docker logs cloudflared --tail 50
docker ps | grep cloudflared
grep CLOUDFLARE_TUNNEL_TOKEN /opt/odoo18/.env
```

**Fix:**
```bash
docker compose restart cloudflared
docker logs cloudflared -f
```

---

## 🔄 BACKUP & RESTORE

### **Quick Backup**

```bash
# Database backup
docker exec Postgres17-Odoo18 pg_dump -U postgres gopokaja | gzip > /opt/odoo18/backups/gopokaja_$(date +%Y-%m-%d).sql.gz

# Filestore backup
tar -czf /opt/odoo18/backups/filestore_$(date +%Y-%m-%d).tar.gz /opt/odoo18/Odoo_data/filestore/

# Config backup
tar -czf /opt/odoo18/backups/config_$(date +%Y-%m-%d).tar.gz /opt/odoo18/.env /opt/odoo18/odoo.conf /opt/odoo18/docker-compose.yaml
```

---

### **Quick Restore**

```bash
# Restore database
gunzip -c /opt/odoo18/backups/gopokaja_2025-05-07.sql.gz | docker exec -i Postgres17-Odoo18 psql -U postgres -d postgres

# Restore filestore
tar -xzf /opt/odoo18/backups/filestore_2025-05-07.tar.gz -C /

# Restart
docker compose restart
```

---

## 🚨 EMERGENCY PROCEDURES

### **Emergency 1: Container Crashed**

```bash
docker ps -a
docker logs [CONTAINER] --tail 100
docker compose restart [CONTAINER]
docker compose down
docker compose up -d
```

---

### **Emergency 2: Out of Memory**

```bash
free -h
docker stats
docker compose stop cloudflared
ps aux --sort=-%mem | head -10
```

---

### **Emergency 3: Disk Full**

```bash
df -h
du -sh /opt/odoo18/* | sort -h
rm -f /opt/odoo18/logs/odoo.log.*.gz
ls -t /opt/odoo18/backups | tail -n +11 | xargs rm -f
```

---

### **Emergency 4: Database Corruption**

```bash
docker exec Postgres17-Odoo18 pg_dump -U postgres gopokaja > /tmp/gopokaja_emergency_backup.sql
docker exec -it Postgres17-Odoo18 psql -U postgres -d gopokaja -c "SELECT COUNT(*) FROM information_schema.tables;"
docker exec -it Postgres17-Odoo18 psql -U postgres -d gopokaja -c "VACUUM ANALYZE;"
docker compose restart Postgres17-18
```

---

### **Emergency 5: Module Broken**

```bash
docker logs Odoo18 -f | grep -i error
docker exec -it Odoo18 odoo --config=/etc/odoo/odoo.conf -d gopokaja -u base --stop-after-init
nano /opt/odoo18/Addons/module_name/...
docker exec -it Odoo18 odoo --config=/etc/odoo/odoo.conf -d gopokaja -i module_name --stop-after-init
```

---

## 📋 QUICK DIAGNOSTIC

```bash
echo "=== Containers ==="
docker ps -a

echo "=== Odoo Logs ==="
docker logs Odoo18 --tail 100

echo "=== PostgreSQL Logs ==="
docker logs Postgres17-Odoo18 --tail 50

echo "=== Permissions ==="
ls -la /opt/odoo18/Odoo_data/

echo "=== Disk Space ==="
df -h /opt/odoo18

echo "=== Database Users ==="
docker exec -it Postgres17-Odoo18 psql -U postgres -c "\du"

echo "=== Test Connection ==="
docker exec -it Postgres17-Odoo18 psql -U andyka -c "SELECT 1"

echo "=== Network ==="
docker network inspect odoo18_Network

echo "=== File Descriptor ==="
ulimit -n
```

---

## 🎯 COMMON CLAUDE PROMPTS (for MCP sessions)

```
"Check Odoo logs and diagnose error"
"Backup the gopokaja database"
"What's using all the disk space?"
"Upgrade the product_kanban_desktop module"
"Is the server healthy?"
"Fix permission denied error"
"Check PostgreSQL connection"
"Restart containers"
"Update docker-compose"
"Full system diagnostic"
```

---

## 🔐 SECURITY NOTES

⚠️ SSH credentials sensitive - don't share!
⚠️ Database password in odoo.conf - don't expose!
⚠️ API keys in .env - don't commit to Git!
✅ Backup regularly
✅ Monitor logs for issues
✅ Update modules regularly

---

## 📞 WHEN TO USE MCP

| Task | Use MCP? |
|------|----------|
| Check logs | ✅ YES |
| Fix permissions | ✅ YES |
| Edit config | ✅ YES |
| Restart container | ✅ YES |
| Run SQL query | ✅ YES |
| Upload files | ❌ NO (use SCP/WinSCP) |
| Deploy code | ⚠️ MAYBE (use Git) |

---

## ✅ MCP VERIFICATION

To verify MCP is connected, Claude can run:

```bash
echo "MCP Connected: $(date)"
docker ps --format "table {{.Names}}\t{{.Status}}"
ls -la /opt/odoo18/
docker exec -it Postgres17-Odoo18 psql -U postgres -c "SELECT version();"
```

If all commands work → **MCP fully connected!** ✅

---

## 📝 VERSION & HISTORY

**Version:** 1.0
**Created:** 2025-05-07
**Purpose:** MCP Integration for Direct Server Access & Troubleshooting
**Status:** Ready for use ✅

---

**Document for: Andyka**
**Server: 192.168.1.47 (Gopokaja Odoo 18)**
**Last Updated: 2025-05-07**

---

## 🎯 HOW TO USE THIS HANDOFF

### **When there's an error:**

1. Open this file
2. Start new Claude chat with MCP enabled
3. Say: "I have an error, use this handoff to help diagnose"
4. Claude will execute commands via MCP
5. Problem solved!

### **Quick commands:**

- Lookup by problem in "TROUBLESHOOTING" section
- Copy exact command from handoff
- Claude executes via MCP
- Done!

### **Emergency:**

- Check "EMERGENCY PROCEDURES" section
- Follow step-by-step
- Claude handles via MCP
- Server restored!

---

**End of Handoff Document**
