# Dataset Ferroviari Europei

## 🌍 Panoramica

Espansione del sistema RailwayAI con dati da **7 nazioni europee** per migliorare la generalizzazione del modello ML su diverse tipologie di reti ferroviarie.

---

## 📊 Paesi Supportati

### ✅ Dati Disponibili

| Paese | Operatore | Coverage | GTFS | Status |
|-------|-----------|----------|------|--------|
| 🇫🇷 **Francia** | SNCF | TGV, Intercités, TER | ✅ | **Scaricato** |
| 🇳🇱 **Paesi Bassi** | NS | IC, Sprinter | ✅ | **Scaricato** |
| 🇮🇹 **Italia** | RFI/Trenitalia | Frecciarossa, IC, Regionale | ✅ | Integrato |
| 🇬🇧 **UK** | Multiple | National Rail | ✅ | Integrato |

### ⏳ In Fase di Acquisizione

| Paese | Operatore | Coverage | Note |
|-------|-----------|----------|------|
| 🇩🇪 **Germania** | Deutsche Bahn | ICE, IC, RE, RB | Download manuale richiesto |
| 🇨🇭 **Svizzera** | SBB/CFF/FFS | IC, RE, S-Bahn | Download manuale richiesto |
| 🇦🇹 **Austria** | ÖBB | Railjet, IC, RE | API disponibile |
| 🇪🇸 **Spagna** | Renfe | AVE, Alvia, MD | Mirror pubblici disponibili |

---

## 🏗️ Architettura

### Moduli Creati

1. **`european_railways.py`**
   - Downloader automatico GTFS da fonti pubbliche
   - Supporto mirror: transport.data.gouv.fr, opentransportdata.swiss, etc.
   - 7 paesi configurati con URL aggiornati

2. **`european_data_parser.py`**
   - Parser unificato GTFS multi-paese
   - Estrazione features: velocità, fermate, tempi viaggio
   - Generazione scenari conflitto sintetici (5000 samples)
   - Output: `data/european_training_data.npz`

3. **`train_european.py`**
   - Training multi-paese con weighted sampling
   - Modello MLP 11K parametri
   - Supporto dispositivi CPU/GPU
   - Early stopping e best model selection

### Pipeline Dati

```
GTFS Feed (ZIP)
    ↓
european_railways.py (download)
    ↓
european_data_parser.py (parsing)
    ↓
european_training_data.npz (650 routes, 87K stops)
    ↓
train_european.py (ML training)
    ↓
scheduler_european.pth (modello trained)
```

---

## 📈 Statistiche Dataset

### Dati Scaricati (Francia + Paesi Bassi)

```
Rotte Totali:        650
Fermate Totali:      87,846
Paesi:               2 (france_sncf, netherlands_ns)

FRANCIA (SNCF):
  - Rotte:           466
  - Fermate:         9,196  
  - Velocità media:  55.5 km/h
  - Coverage:        TGV alta velocità + TER regionali

PAESI BASSI (NS):
  - Rotte:           184
  - Fermate:         78,650
  - Velocità media:  100.0 km/h
  - Coverage:        Intercity + Sprinter (rete molto densa)
```

### Dataset Training Generato

```
File:                data/european_training_data.npz
Route Features:      (650, 5) - normalizzato [0-1]
Adjacency Matrix:    (87846, 87846) - grafo rete
Conflict Scenarios:  5,000 scenari sintetici
```

### Modello Trained

```
File:                models/scheduler_european.pth
Architettura:        MLP (5 → 128 → 64 → 32 → 1)
Parametri:           11,137
Training Loss:       0.0812
Validation Loss:     0.0810
Epochs:              11 (early stopping)
Device:              CPU (compatibile GPU)
```

---

## 🚀 Utilizzo

### 1. Scarica Dati GTFS

```bash
# Mostra paesi disponibili
python python/data_acquisition/european_railways.py --list

# Scarica paesi specifici
python python/data_acquisition/european_railways.py \
  --countries france_sncf netherlands_ns switzerland_sbb

# Scarica tutti
python python/data_acquisition/european_railways.py --all
```

### 2. Parsa e Genera Dataset

```bash
python python/data_acquisition/european_data_parser.py \
  --input-dir data/european \
  --output data/european_training_data.npz
```

### 3. Training Modello

```bash
python python/training/train_european.py \
  --epochs 50 \
  --batch-size 64 \
  --lr 0.001 \
  --output models/scheduler_european.pth
```

### 4. Integrazione con C++

Il modello può essere esportato in ONNX per utilizzo con il motore C++:

```python
import torch
from python.training.train_european import SimpleSchedulerNet

# Carica modello
model = SimpleSchedulerNet(input_dim=5)
checkpoint = torch.load('models/scheduler_european.pth')
model.load_state_dict(checkpoint['model_state_dict'])

# Export ONNX
dummy_input = torch.randn(1, 5)
torch.onnx.export(model, dummy_input, "models/scheduler_european.onnx")
```

---

## 🌟 Caratteristiche Reti per Paese

### Velocità Media

| Paese | Velocità | Tipo Rete |
|-------|----------|-----------|
| 🇪🇸 Spagna | **250 km/h** | AVE (alta velocità) |
| 🇫🇷 Francia | **220 km/h** | TGV (alta velocità) |
| 🇮🇹 Italia | **200 km/h** | Frecciarossa |
| 🇩🇪 Germania | **180 km/h** | ICE |
| 🇦🇹 Austria | **170 km/h** | Railjet |
| 🇨🇭 Svizzera | **150 km/h** | Rete mista |
| 🇳🇱 Paesi Bassi | **140 km/h** | Rete densa urbana |

### Puntualità

| Paese | Tasso | Note |
|-------|-------|------|
| 🇨🇭 Svizzera | **92%** | Migliore in Europa |
| 🇳🇱 Paesi Bassi | **92%** | Rete efficientissima |
| 🇪🇸 Spagna | **90%** | AVE molto affidabile |
| 🇫🇷 Francia | **88%** | TGV ben gestito |
| 🇦🇹 Austria | **85%** | Standard alto |
| 🇮🇹 Italia | **82%** | In miglioramento |
| 🇩🇪 Germania | **75%** | Rete complessa |

### Elettrificazione

| Paese | % Elettrificata | Note |
|-------|-----------------|------|
| 🇨🇭 Svizzera | **100%** | Completamente elettrica! |
| 🇳🇱 Paesi Bassi | **95%** | Quasi completa |
| 🇩🇪 Germania | **90%** | Rete estesa |
| 🇦🇹 Austria | **88%** | Alta copertura |
| 🇫🇷 Francia | **85%** | Focus TGV |
| 🇪🇸 Spagna | **80%** | AVE + linee tradizionali |
| 🇮🇹 Italia | **75%** | Mix diesel/elettrico |

---

## 📝 Fonti Dati

### GTFS Feed Pubblici

- **Francia**: [transport.data.gouv.fr](https://transport.data.gouv.fr)
  - Direct: `https://eu.ftp.opendatasoft.com/sncf/gtfs/export-ter-gtfs-last.zip`
  
- **Paesi Bassi**: [ovapi.nl](http://gtfs.ovapi.nl)
  - Direct: `http://gtfs.ovapi.nl/nl/gtfs-nl.zip`

- **Germania**: [data.deutschebahn.com](https://data.deutschebahn.com)
  - Richiede download manuale

- **Svizzera**: [opentransportdata.swiss](https://opentransportdata.swiss)
  - Dataset pubblici aggiornati annualmente

- **Altri**: [TransitFeeds](https://transitfeeds.com), [Mobility Database](https://database.mobilitydata.org)

### API Real-Time (Futuro)

- **SNCF**: [SNCF Open Data API](https://ressources.data.sncf.com)
- **NS**: [NS API](https://www.ns.nl/en/travel-information/ns-api)
- **DB**: [DB Open Data Portal](https://data.deutschebahn.com)
- **ÖBB**: [ÖBB Open Data](https://data.oebb.at)

---

## 🎯 Obiettivi Raggiunti

✅ **Download Automatico**: 2/7 paesi scaricati automaticamente  
✅ **Parser Unificato**: 650 rotte parsate da Francia + Paesi Bassi  
✅ **Dataset Training**: 87K fermate, 5K scenari conflitto  
✅ **Modello ML**: Training completato (val_loss: 0.0810)  
✅ **Documentazione**: Completa con istruzioni uso  

---

## 🔜 Prossimi Passi

1. **Completare Download**: Germania, Svizzera, Austria, Spagna
2. **API Real-Time**: Integrare dati in tempo reale
3. **Cross-Country Scenarios**: Scenari conflitto internazionali (es. Parigi-Amsterdam)
4. **Model Evaluation**: Benchmark su reti diverse
5. **ONNX Export**: Integrazione con C++ engine
6. **Multi-Language Support**: Supporto nomi stazioni multilingua

---

## 📚 Riferimenti

- [GTFS Specification](https://gtfs.org)
- [European Railway Agency](https://www.era.europa.eu)
- [Mobility Database](https://database.mobilitydata.org)
- [OpenTransportData.swiss](https://opentransportdata.swiss)
- [SNCF Open Data](https://ressources.data.sncf.com)

---

## 📧 Supporto

Per problemi o domande sull'integrazione dati europei:
- Issue GitHub: [RailwayAI/issues](https://github.com/manvalan/RailwayAI/issues)
- Documentazione: `EUROPEAN_DATA.md` (questo file)

---

**Ultimo Aggiornamento**: 19 Novembre 2025  
**Versione Dataset**: 1.0  
**Paesi Integrati**: 4 (IT, UK, FR, NL)  
**Paesi In Sviluppo**: 3 (DE, CH, AT)
