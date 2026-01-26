# 🚀 Aggiornamento Portainer - Istruzioni Rapide

## ✅ Commit e Push Completati!

Le modifiche sono state pushate su GitHub: `9ef334c`

---

## 📋 Prossimi Passi su Portainer

### 1. Accedi a Portainer
Vai a: **http://82.165.138.64:8080/**

### 2. Trova il Container Railway AI
- Click su **Containers** nel menu laterale
- Cerca il container `railway-ai` o simile

### 3. Recreate il Container
1. Click sul container
2. Click sul pulsante **⟳ Recreate** in alto
3. Nella finestra di dialogo:
   - ✅ Abilita **"Pull latest image"**
   - ✅ Abilita **"Re-pull image"** (se disponibile)
4. Click **Recreate**

### 4. Attendi il Restart
Il container si riavvierà automaticamente con le nuove modifiche.

---

## 🔍 Verifica che Funzioni

### Controlla i Logs
1. Click sul container
2. Click su **Logs**
3. Cerca queste righe:
   ```
   Initializing route planner and temporal simulator
   Starting Railway AI Scheduler API v2.0.0...
   ```

### Test API
```bash
# Health check
curl http://82.165.138.64:8002/api/v1/health

# Dovrebbe rispondere:
# {"status":"healthy","model_loaded":true,"version":"1.0.0",...}
```

---

## 🎯 Nuovo Endpoint Disponibile

Dopo l'aggiornamento, avrai accesso a:

**`POST /api/v1/optimize_scheduled`**

Questo endpoint supporta:
- ✅ Route planning automatico
- ✅ Simulazione temporale
- ✅ Treni in direzioni opposte
- ✅ Rilevamento conflitti futuri
- ✅ Ottimizzazione dei tempi di sosta (Dwell Delays)

### 🚀 Novità per reti complesse (59 stazioni)
Per risolvere i conflitti su reti grandi, abbiamo potenziato l'algoritmo. Ti consiglio di:
1.  Aumentare il parametro **`max_iterations`** a almeno `120` (i treni impiegano più di 60m per completare il percorso).
2.  Controllare i **Logs di Portainer**: ora il server logga esplicitamente i `dwell_delays`. Se vedi ritardi nei log ma l'app segna "Shifted 0.0m", significa che l'app sta ignorando le soste suggerite.
3.  (Opzionale) Puoi passare `ga_max_iterations: 300` e `ga_population_size: 100` nel JSON per una ricerca ancora più approfondita.

---

## 📞 Se Qualcosa Va Storto

### Problema: Container non si avvia
**Soluzione:**
1. Vai ai Logs del container
2. Cerca errori di import
3. Se necessario, fai **Rebuild** invece di Recreate

### Problema: Endpoint non trovato
**Soluzione:**
1. Verifica che il container sia stato ricreato
2. Controlla i logs per "Starting Railway AI Scheduler API v2.0.0"
3. Prova a fare restart manuale del container

---

## ✨ Tutto Pronto!

Una volta completato l'aggiornamento su Portainer, potrai:
1. Usare il nuovo endpoint `/api/v1/optimize_scheduled`
2. Testare lo scenario Bywater-Nobottle
3. Gestire treni con partenze programmate

**Buon deployment! 🚂**
