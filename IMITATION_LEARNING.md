# 🎓 Imitation Learning Pipeline

## Problema
Il training MARL puro (reinforcement learning) è **troppo lento** - richiede mesi per convergere e regredisce frequentemente.

## Soluzione: Imitation Learning
Invece di esplorare casualmente, la rete neurale **impara da un esperto** (l'algoritmo genetico GA) che già sa risolvere i conflitti.

### Vantaggi
- ⚡ **100x più veloce**: Giorni invece di mesi
- 🎯 **Più stabile**: Impara da soluzioni corrette, non da errori
- 📊 **Usa dati reali**: Orari ferroviari europei (GTFS)
- 🔄 **Migliorabile**: Può essere raffinato con RL dopo

---

## 🚀 Quick Start

### Opzione 1: Script Automatico (Raccomandato)
```bash
./scripts/run_imitation_pipeline.sh
```

Questo script:
1. Scarica dati GTFS europei
2. Genera 10,000 esempi di training dal GA
3. Addestra la rete neurale
4. (Opzionale) Raffina con RL

### Opzione 2: Step Manuali

#### 1. Scarica Dati GTFS
```bash
python3 scripts/download_gtfs_europe.py
```

#### 2. Genera Dataset Esperto
```bash
python3 python/training/generate_expert_dataset.py \
    --examples 10000 \
    --output data/expert_demonstrations
```

#### 3. Addestra con Imitation Learning
```bash
python3 python/training/train_imitation.py \
    --dataset data/expert_demonstrations/expert_dataset.pt \
    --output models/imitation \
    --epochs 50
```

#### 4. (Opzionale) Fine-tune con RL
```bash
python3 python/marl_scheduling/train_mappo.py \
    --checkpoint models/imitation/best_imitation_model.pth \
    --curriculum \
    --level 2 \
    --episodes 1000
```

---

## 📊 Come Funziona

### 1. Expert Dataset Generation
```
Scenari Reali (GTFS) → Introduci Conflitti → Risolvi con GA → Salva (stato, azione)
```

Il GA risolve migliaia di scenari realistici. Per ogni soluzione, salviamo:
- **Stato**: Posizione treni, velocità, occupazione binari
- **Azione**: Cosa ha fatto il GA (wait/slow/normal/fast)

### 2. Supervised Learning
```
Dataset Esperto → Rete Neurale → Impara a imitare GA
```

La rete impara a prevedere le azioni del GA dato uno stato.
- Loss: Cross-entropy (classificazione)
- Metrica: Accuracy (% azioni corrette)

### 3. (Opzionale) RL Fine-tuning
```
Modello Pre-addestrato → MAPPO → Raffina su scenari complessi
```

Parte da pesi già buoni invece che casuali = converge molto più velocemente.

---

## 📈 Performance Attese

### Imitation Learning (Solo)
- **Training time**: 2-4 ore (GPU) o 8-12 ore (CPU)
- **Accuracy attesa**: 75-85%
- **Pronto per**: Scenari semplici/medi

### Imitation + RL Fine-tuning
- **Training time**: +1-2 giorni
- **Accuracy attesa**: 90-95%
- **Pronto per**: Scenari complessi/produzione

---

## 🔧 Configurazione

### Dataset Size
```bash
# Più esempi = migliore generalizzazione
python3 python/training/generate_expert_dataset.py --examples 50000
```

### Training Hyperparameters
```bash
python3 python/training/train_imitation.py \
    --epochs 100 \
    --batch-size 512 \
    --lr 0.001
```

### Conflict Rate
Modifica in `generate_expert_dataset.py`:
```python
conflict_rate = 0.5  # 50% dei treni in conflitto (più difficile)
```

---

## 📁 Output

```
data/expert_demonstrations/
├── expert_dataset.pt          # Dataset di training
└── metadata.json              # Info sul dataset

models/imitation/
├── best_imitation_model.pth   # Miglior modello (usa questo!)
├── final_imitation_model.pth  # Modello finale
└── training_history.json      # Metriche di training
```

---

## 🐛 Troubleshooting

### "No scenarios loaded"
```bash
# Assicurati di avere scenari reali
ls scenarios/*_real*.json

# Se mancano, scarica dati OSM
python3 scripts/fetch_osm_rail.py --area "Toscana" --output scenarios/toscana_real.json
```

### "GA optimization failed"
```bash
# Riduci complessità scenari o aumenta iterazioni GA
# In generate_expert_dataset.py:
max_iterations=500  # invece di 200
```

### "Out of memory"
```bash
# Riduci batch size
python3 python/training/train_imitation.py --batch-size 128
```

---

## 🎯 Next Steps

1. **Test il modello**:
   ```bash
   python3 python/training/evaluate_model.py \
       --model models/imitation/best_imitation_model.pth \
       --scenario scenarios/siena_empoli_real.json
   ```

2. **Deploy in produzione**:
   - Copia `best_imitation_model.pth` in `models/`
   - Riavvia API server
   - Il modello sarà usato automaticamente

3. **Monitora performance**:
   - Usa dashboard web per vedere metriche
   - Colleziona feedback da utenti
   - Rigenera dataset con nuovi scenari problematici

---

## 📚 Riferimenti

- **Imitation Learning**: [Paper](https://arxiv.org/abs/1606.03476)
- **Behavioral Cloning**: [Tutorial](https://spinningup.openai.com/en/latest/algorithms/bc.html)
- **GTFS Spec**: [Reference](https://gtfs.org/reference/static)

---

## ⚠️ Note Importanti

1. **GA non è perfetto**: Il modello imparerà anche gli errori del GA. Per questo il fine-tuning RL è importante.

2. **Dati reali cruciali**: Più scenari reali usi, meglio generalizza la rete.

3. **Validazione necessaria**: Testa sempre su scenari mai visti prima del deploy.

4. **Backup checkpoint**: Salva regolarmente i modelli durante il training.
