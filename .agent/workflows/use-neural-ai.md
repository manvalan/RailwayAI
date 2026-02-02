---
description: Come utilizzare correttamente la Rete Neurale (AI) per l'ottimizzazione
---

Per utilizzare la vera intelligenza artificiale del sistema (Neural Network) ed evitare confusione con l'algoritmo genetico:

1. **Verifica il Modello**: Assicurati che un file `.pth` sia presente in `api/models/` o `models/`.
2. **Endpoint Corretto**: Usa sempre l'endpoint `/api/v1/optimize`. 
3. **Payload**: Invia una lista di treni con lo stato attuale (`position_km`, `velocity_kmh`, `current_track`, `destination_station`).
4. **Validazione**: Se la risposta contiene `resolutions` con un campo `confidence`, stai usando la Rete Neurale. Se vedi riferimenti a "generazioni" o "fitness", stai erroneamente usando l'Algoritmo Genetico.

// turbo
5. **Esegui un Test AI**: Usa lo script `verify_ai_debug.py` per confermare che il backend stia usando la rete neurale.
