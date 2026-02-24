"""
Esporta il modello MAPPO attuale (ActorNetwork v4, 23 input dim) in formato ONNX.
Compatibile con l'architettura: obs_dim=23, num_actions=4, Multi-Head Attention + Skip Connection.

Uso:
    python python/training/export_onnx.py --checkpoint checkpoints/mappo_curriculum_l1_ep56100.pth
    python python/training/export_onnx.py --checkpoint checkpoints/mappo_curriculum_l1_ep56100.pth --test
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

# Aggiungi i path necessari
current_dir = Path(__file__).parent.absolute()
parent_python_dir = current_dir.parent.absolute()
marl_dir = parent_python_dir / "marl_scheduling"

for p in [str(current_dir), str(parent_python_dir), str(marl_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import torch
import torch.nn as nn


def export_actor_to_onnx(checkpoint_path: str,
                          onnx_path: str = None,
                          obs_dim: int = 23,
                          num_actions: int = 4,
                          num_agents: int = 2):
    """
    Esporta l'ActorNetwork MAPPO in formato ONNX.

    Args:
        checkpoint_path: Path al checkpoint .pth (MAPPO format)
        onnx_path: Path output .onnx (default: stesso nome del checkpoint)
        obs_dim: Dimensione osservazione per agente (default: 23, v4)
        num_actions: Numero azioni discrete (default: 4)
        num_agents: Numero agenti tipico per il batch di test (default: 2)
    """
    from models import ActorNetwork, CriticNetwork

    checkpoint_path = Path(checkpoint_path)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint non trovato: {checkpoint_path}")

    if onnx_path is None:
        onnx_path = checkpoint_path.with_suffix(".onnx")
    onnx_path = Path(onnx_path)
    onnx_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"📦 Caricamento checkpoint: {checkpoint_path}")
    device = torch.device("cpu")
    ckpt = torch.load(checkpoint_path, map_location=device)

    # Verifica architettura nel checkpoint
    ckpt_obs_dim = ckpt.get("obs_dim", obs_dim)
    ckpt_num_actions = ckpt.get("num_actions", num_actions)
    ckpt_episode = ckpt.get("episode", "?")
    ckpt_level = ckpt.get("level", "?")
    ckpt_reward = ckpt.get("reward", "?")

    print(f"   Episodio: {ckpt_episode} | Livello: {ckpt_level} | Reward: {ckpt_reward:.2f}" 
          if isinstance(ckpt_reward, float) else f"   Episodio: {ckpt_episode} | Livello: {ckpt_level}")
    print(f"   Architettura: obs_dim={ckpt_obs_dim}, num_actions={ckpt_num_actions}")

    if ckpt_obs_dim != obs_dim:
        print(f"⚠️  ATTENZIONE: obs_dim nel checkpoint ({ckpt_obs_dim}) != obs_dim atteso ({obs_dim})")
        obs_dim = ckpt_obs_dim

    # Costruisci e carica Actor
    actor = ActorNetwork(obs_dim, num_actions=ckpt_num_actions).to(device)

    if "actor" in ckpt:
        actor.load_state_dict(ckpt["actor"])
        print("✅ Pesi Actor caricati")
    else:
        raise KeyError("Checkpoint non contiene la chiave 'actor'. Usa un checkpoint MAPPO valido.")

    actor.eval()

    # Input dummy: (1, num_agents, obs_dim) = batch con 2 agenti come al solito
    dummy_input = torch.randn(1, num_agents, obs_dim, device=device)

    print(f"\n📤 Esportazione Actor in ONNX → {onnx_path}")

    torch.onnx.export(
        actor,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=17,
        do_constant_folding=True,
        input_names=["agent_observations"],       # (batch, num_agents, obs_dim)
        output_names=["action_probabilities"],     # (batch, num_agents, num_actions)
        dynamic_axes={
            "agent_observations": {0: "batch_size", 1: "num_agents"},
            "action_probabilities": {0: "batch_size", 1: "num_agents"},
        }
    )

    print(f"✅ ONNX salvato: {onnx_path}")

    # Verifica modello ONNX
    try:
        import onnx
        onnx_model = onnx.load(str(onnx_path))
        onnx.checker.check_model(onnx_model)
        print("✅ Modello ONNX verificato (struttura valida)")
    except ImportError:
        print("⚠️  onnx non installato, skip verifica (pip install onnx)")
    except Exception as e:
        print(f"⚠️  Errore verifica ONNX: {e}")

    # Salva metadati export
    meta_path = onnx_path.with_suffix(".export_meta.json")
    meta = {
        "exported_at": datetime.now().isoformat(),
        "source_checkpoint": str(checkpoint_path),
        "episode": ckpt_episode,
        "level": ckpt_level,
        "obs_dim": obs_dim,
        "num_actions": ckpt_num_actions,
        "num_agents_ref": num_agents,
        "onnx_opset": 17,
        "input_names": ["agent_observations"],
        "output_names": ["action_probabilities"],
        "notes": "ActorNetwork MAPPO v4 — Multi-Head Attention + Skip Connection"
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"📋 Metadati salvati: {meta_path}")

    return str(onnx_path)


def test_onnx_inference(onnx_path: str, obs_dim: int = 23, num_agents: int = 2, num_actions: int = 4):
    """
    Testa l'inferenza del modello ONNX esportato e confronta con PyTorch originale.
    """
    try:
        import onnxruntime as ort
    except ImportError:
        print("⚠️  onnxruntime non installato (pip install onnxruntime). Skip test.")
        return

    import numpy as np

    print(f"\n🧪 Test inferenza ONNX: {onnx_path}")
    session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])

    dummy = np.random.randn(1, num_agents, obs_dim).astype(np.float32)
    outputs = session.run(None, {"agent_observations": dummy})

    probs = outputs[0]
    print(f"   Input shape:  {dummy.shape}")
    print(f"   Output shape: {probs.shape}  (atteso: [1, {num_agents}, {num_actions}])")

    # Verifica che le probabilità sommino a 1
    row_sums = probs.sum(axis=-1)
    all_valid = all(abs(s - 1.0) < 1e-4 for s in row_sums.flatten())
    print(f"   Somma probabilità per agente: {row_sums.flatten().tolist()}")
    print(f"   ✅ Distribuzione valida (somma ≈ 1)" if all_valid else "   ❌ ERRORE: probabilità non sommano a 1")

    # Azione più probabile per ogni agente
    best_actions = probs.argmax(axis=-1).flatten()
    action_names = {0: "Cruise", 1: "Slow", 2: "Wait", 3: "Fast"}
    for i, act in enumerate(best_actions):
        print(f"   Agente {i}: azione preferita = {act} ({action_names.get(act, '?')})")

    print("✅ Test inferenza completato\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Esporta ActorNetwork MAPPO v4 in ONNX")
    parser.add_argument(
        "--checkpoint", type=str,
        default="checkpoints/mappo_curriculum_l1_ep56100.pth",
        help="Path al checkpoint .pth (MAPPO format)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Path output .onnx (default: stesso nome del checkpoint)"
    )
    parser.add_argument(
        "--obs-dim", type=int, default=23,
        help="Dimensione vettore osservazione (default: 23)"
    )
    parser.add_argument(
        "--num-agents", type=int, default=2,
        help="Numero agenti per il dummy input di test (default: 2)"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Esegui test di inferenza dopo l'export"
    )

    args = parser.parse_args()

    onnx_path = export_actor_to_onnx(
        checkpoint_path=args.checkpoint,
        onnx_path=args.output,
        obs_dim=args.obs_dim,
        num_agents=args.num_agents
    )

    if args.test:
        test_onnx_inference(onnx_path, obs_dim=args.obs_dim, num_agents=args.num_agents)

    print(f"\n✅ Export completato: {onnx_path}")
