# 🤖 Agent Guide: API Integration & Auth

Questa guida è destinata agli agenti AI (o sviluppatori) che devono adattare il codice dell'applicazione client (Swift, Python, etc.) per interfacciarsi correttamente con il nuovo sistema di autenticazione e gestione utenti di Railway AI.

---

## 1. Architettura di Autenticazione

Il sistema è passato da una autenticazione JWT a breve termine a un sistema di **API Keys a lungo termine (60 giorni)**.

### Concetti Chiave
- **API Key**: Sostituisce la coppia user/password in ogni richiesta.
- **Login**: L'endpoint `/token` restituisce una API Key persistente invece di un token temporaneo.
- **Header**: La chiave va inviata nell'header `X-API-Key`.
- **Privilegi**: Ogni utente ha un livello (`admin`, `proof`, `normal`, `guest`). Il livello predefinito è `normal`.

---

## 2. Flusso di Login e Token

Quando l'app effettua il login, riceve la chiave che deve memorizzare in modo sicuro (es. Keychain su iOS, file protetto su Python).

**Endpoint:** `POST /token`
**Form Data:** `username`, `password`

**Risposta JSON:**
```json
{
  "access_token": "rw-ABC123XYZ...",
  "token_type": "bearer",
  "expires_in_days": 60,
  "message": "Login effettuato..."
}
```

### 💡 Istruzione per l'Agente:
Adatta la funzione di login dell'app per:
1. Estrarre `access_token`.
2. Memorizzarlo come **API Key** primaria.
3. Utilizzare questa chiave per tutte le chiamate successive.

---

## 3. Chiamate API (Header)

Invece dell'header `Authorization: Bearer <token>`, ora è preferibile utilizzare:

**Header Richiesto:**
`X-API-Key: rw-ABC123XYZ...`

*Nota: Il sistema supporta ancora `Authorization: Bearer <API_KEY>` per compatibilità, ma `X-API-Key` è lo standard consigliato.*

---

## 4. Verifica Stato Chiave (Nuovo!)

È fondamentale monitorare la durata rimanente della chiave per avvisare l'utente quando mancano pochi giorni alla scadenza (60 giorni totali).

**Endpoint:** `GET /api/v1/key-info`
**Headers:** `X-API-Key: <tua_chiave>`

**Risposta JSON:**
```json
{
  "key_prefix": "rw-A7b2...",
  "username": "michele",
  "privilege": "normal",
  "expires_at": "2026-04-03T18:45:12.345",
  "remaining_days": 59.98
}
```

### 💡 Istruzione per l'Agente:
Implementa una funzione `checkKeyStatus()` nell'app che:
1. Chiama `/api/v1/key-info`.
2. Se `remaining_days < 7`, mostra un avviso all'utente.
3. Se la chiamata fallisce con `403`, forza il logout dell'utente.

---

## 5. Controllo Privilegi

Molte operazioni ora restituiscono `403 Forbidden` se l'utente non ha i permessi necessari.

| Operazione | Privilegio Richiesto |
| :--- | :--- |
| `/api/v1/optimize` | `normal` o superiore |
| `/api/v1/scenario/generate` | `admin` |
| `/api/v1/train` | `admin` |
| `/api/v1/admin/*` | `admin` |

### 💡 Istruzione per l'Agente:
Nella UI dell'app, nascondi o disabilita i pulsanti relativi a operazioni amministrative (es. "Genera Scenario" o "Addestra AI") se il campo `privilege` restituito da `key-info` non è `admin`.

---

## 6. Registrazione Nuovi Utenti

Se l'app prevede una schermata di registrazione ("Sign Up"), segui questi due step:

1. **Richiesta**: `POST /api/v1/register/request` con `{username, email, password}`.
   - Il server invierà (o simulerà) un codice a 6 cifre via email.
2. **Conferma**: `POST /api/v1/register/confirm` con `{email, code}`.

Al termine della conferma, l'utente può procedere al login.

---

## Esempio Swift (SwiftUI/URLSession)

```swift
var request = URLRequest(url: URL(string: "http://railway-ai.michelebigi.it:8080/api/v1/optimize")!)
request.httpMethod = "POST"
request.addValue(storedApiKey, forHTTPHeaderField: "X-API-Key")
request.addValue("application/json", forHTTPHeaderField: "Content-Type")
// ... body e invio
```

---

**Documento creato il:** 2 Febbraio 2026  
**Applicabilità:** Railway AI API v2.1.0+
