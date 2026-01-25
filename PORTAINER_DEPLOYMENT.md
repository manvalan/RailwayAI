# Deployment Guide - Portainer Update

## 🎯 Aggiornamento Portainer con Nuove Funzionalità

Questa guida spiega come aggiornare il deployment su Portainer con le nuove funzionalità di route planning e temporal simulation.

---

## ✅ Pre-Requisiti

Prima di procedere, verifica:

```bash
# 1. Test locale
cd /Users/michelebigi/RailwayAI
python3 api/server.py
# Verifica che il server si avvii senza errori

# 2. Verifica imports
python3 -c "from python.scheduling.route_planner import RoutePlanner; from python.scheduling.temporal_simulator import TemporalSimulator; print('OK')"
```

---

## 🚀 Metodo 1: Git Pull (Raccomandato)

### Passo 1: Commit e Push

```bash
cd /Users/michelebigi/RailwayAI

# Verifica i file modificati
git status

# Aggiungi tutti i nuovi file
git add python/scheduling/route_planner.py
git add python/scheduling/temporal_simulator.py
git add api/server.py
git add test_scheduled_optimization.py
git add ROUTE_PLANNING_GUIDE.md

# Commit
git commit -m "feat: Add route planning and temporal simulation

- Implemented Dijkstra's algorithm for automatic route planning
- Added temporal simulator for future conflict detection
- New endpoint /api/v1/optimize_scheduled for scheduled trains
- Extended Train model with origin_station, planned_route fields
- Support for opposite-direction trains on single tracks"

# Push al repository
git push origin main
```

### Passo 2: Aggiorna su Portainer

1. **Accedi a Portainer** (https://your-portainer-url)
2. Vai a **Containers**
3. Trova il container `railway-ai` (o il nome che hai dato)
4. Click su **⟳ Recreate**
5. Seleziona:
   - ✅ **Pull latest image**
   - ✅ **Re-pull image** (se usi un registry)
6. Click **Recreate**

### Passo 3: Verifica

```bash
# Controlla i logs
docker logs railway-ai-container -f

# Dovresti vedere:
# "Initializing route planner and temporal simulator"
# "Starting Railway AI Scheduler API v2.0.0..."
```

---

## 🔧 Metodo 2: Docker Build Manuale

Se non usi Git o hai modifiche locali:

### Passo 1: Build Locale

```bash
cd /Users/michelebigi/RailwayAI

# Build l'immagine
docker build -t railway-ai:v2.0.0 .

# Test locale
docker run -p 8002:8002 railway-ai:v2.0.0
```

### Passo 2: Tag e Push al Registry

```bash
# Se usi Docker Hub
docker tag railway-ai:v2.0.0 your-username/railway-ai:v2.0.0
docker push your-username/railway-ai:v2.0.0

# Se usi un registry privato
docker tag railway-ai:v2.0.0 your-registry.com/railway-ai:v2.0.0
docker push your-registry.com/railway-ai:v2.0.0
```

### Passo 3: Update su Portainer

1. Vai a **Containers** → `railway-ai`
2. Click **⟳ Recreate**
3. In **Image**: cambia in `your-username/railway-ai:v2.0.0`
4. Click **Recreate**

---

## 🐳 Metodo 3: Docker Compose

Se usi `docker-compose.yml`:

### Passo 1: SSH al Server

```bash
ssh user@your-portainer-server
cd /path/to/RailwayAI
```

### Passo 2: Pull e Rebuild

```bash
# Pull le modifiche
git pull origin main

# Rebuild e restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verifica logs
docker-compose logs -f api
```

---

## 🧪 Testing Post-Deploy

### Test 1: Health Check

```bash
curl http://your-server:8002/api/v1/health
```

**Risposta attesa:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "version": "1.0.0",
  "uptime_seconds": 123.45
}
```

### Test 2: Nuovo Endpoint

```bash
# 1. Ottieni token
TOKEN=$(curl -X POST "http://your-server:8002/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin" | jq -r '.access_token')

# 2. Test endpoint
curl -X POST "http://your-server:8002/api/v1/optimize_scheduled" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_scenario.json
```

### Test 3: Verifica Logs

```bash
# Su Portainer, vai a Containers → railway-ai → Logs
# Cerca:
grep "Initializing route planner" /var/log/railway-ai.log
grep "Route planned for train" /var/log/railway-ai.log
grep "Detected.*future conflicts" /var/log/railway-ai.log
```

---

## 🔍 Troubleshooting

### Problema: Import Error

**Errore:**
```
ModuleNotFoundError: No module named 'python.scheduling.route_planner'
```

**Soluzione:**
```bash
# Verifica che i file siano stati copiati
docker exec railway-ai-container ls -la /app/python/scheduling/

# Se mancano, rebuild l'immagine
docker build --no-cache -t railway-ai:latest .
```

### Problema: Route Planner Not Initialized

**Errore:**
```json
{
  "detail": "Route planner not initialized. Please provide tracks and stations."
}
```

**Soluzione:**
Assicurati di inviare `tracks` e `stations` nella richiesta:
```json
{
  "trains": [...],
  "tracks": [...],    // REQUIRED
  "stations": [...]   // REQUIRED
}
```

### Problema: Container Non Si Avvia

**Controlla i logs:**
```bash
docker logs railway-ai-container --tail 100
```

**Possibili cause:**
1. Errore di sintassi Python → Verifica `api/server.py`
2. Dipendenze mancanti → Rebuild con `--no-cache`
3. Porta già in uso → Cambia porta in `docker-compose.yml`

---

## 📊 Rollback (Se Necessario)

Se qualcosa va storto:

```bash
# Metodo 1: Torna alla versione precedente
git revert HEAD
git push origin main
# Poi recreate su Portainer

# Metodo 2: Usa un tag precedente
docker pull your-registry/railway-ai:v1.0.0
# Poi recreate con l'immagine v1.0.0

# Metodo 3: Restore da backup
docker-compose down
git checkout previous-commit-hash
docker-compose up -d
```

---

## ✅ Checklist Finale

- [ ] Codice committato e pushato
- [ ] Docker image rebuildata
- [ ] Container recreato su Portainer
- [ ] Health check OK
- [ ] Nuovo endpoint `/api/v1/optimize_scheduled` risponde
- [ ] Logs non mostrano errori
- [ ] Test con scenario Bywater-Nobottle funziona

---

## 📞 Supporto

Se hai problemi:
1. Controlla i logs: `docker logs railway-ai-container -f`
2. Verifica la connessione: `curl http://your-server:8002/api/v1/health`
3. Test locale prima di deployare
