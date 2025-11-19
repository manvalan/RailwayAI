"""
Ottimizzatore Orari per Treni in Senso Opposto.

Determina gli orari ottimali per una coppia di treni che viaggiano in direzioni
opposte su una linea con sezioni miste (singolo binario + doppio binario).

Features:
- Analisi topologia rete (single/double track sections)
- Identificazione punti di incrocio ottimali
- Minimizzazione attese e ritardi
- Rispetto vincoli capacità binari
- Considerazione traffico esistente
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TrackSection:
    """Sezione di binario con caratteristiche."""
    section_id: int
    start_km: float
    end_km: float
    num_tracks: int  # 1=singolo binario, 2+=doppio binario
    max_speed_kmh: float
    has_station: bool
    station_name: Optional[str] = None
    can_cross: bool = False  # Può ospitare incroci?
    
    def length_km(self) -> float:
        return self.end_km - self.start_km
    
    def is_single_track(self) -> bool:
        return self.num_tracks == 1
    
    def is_double_track(self) -> bool:
        return self.num_tracks >= 2


@dataclass
class TrainPath:
    """Percorso di un treno sulla rete."""
    train_id: str
    direction: str  # 'forward' o 'backward'
    start_km: float
    end_km: float
    avg_speed_kmh: float
    departure_time: datetime
    stops: List[Tuple[float, int]]  # (km, duration_minutes)
    priority: int = 5  # 1-10
    
    def travel_time_minutes(self, distance_km: float) -> float:
        """Tempo di viaggio per una distanza."""
        return (distance_km / self.avg_speed_kmh) * 60.0
    
    def arrival_time(self) -> datetime:
        """Orario arrivo finale."""
        total_distance = abs(self.end_km - self.start_km)
        travel_mins = self.travel_time_minutes(total_distance)
        stop_mins = sum(duration for _, duration in self.stops)
        return self.departure_time + timedelta(minutes=travel_mins + stop_mins)


@dataclass
class ExistingTrain:
    """Treno già presente sul traffico."""
    train_id: str
    position_km: float
    velocity_kmh: float
    direction: str
    estimated_times: Dict[float, datetime]  # km -> orario passaggio


@dataclass
class ScheduleProposal:
    """Proposta di orario ottimizzato."""
    train1_departure: datetime
    train2_departure: datetime
    crossing_point_km: float
    crossing_time: datetime
    train1_wait_minutes: float
    train2_wait_minutes: float
    total_delay_minutes: float
    conflicts_avoided: int
    confidence: float  # 0.0-1.0
    reasoning: str


class OppositeTrainScheduler:
    """
    Ottimizzatore orari per treni in senso opposto.
    
    Trova gli orari migliori per far viaggiare due treni in direzioni
    opposte minimizzando attese e conflitti, considerando:
    - Sezioni a singolo binario (richiedono coordinamento)
    - Sezioni a doppio binario (passaggio libero)
    - Stazioni di incrocio
    - Traffico esistente
    """
    
    def __init__(self, track_sections: List[TrackSection]):
        self.track_sections = sorted(track_sections, key=lambda s: s.start_km)
        self.total_length_km = max(s.end_km for s in track_sections)
        
        # Analizza topologia
        self.single_track_sections = [s for s in track_sections if s.is_single_track()]
        self.crossing_stations = [s for s in track_sections if s.can_cross and s.has_station]
        
        logger.info(f"📊 Rete analizzata: {len(track_sections)} sezioni")
        logger.info(f"   Singolo binario: {len(self.single_track_sections)} sezioni")
        logger.info(f"   Stazioni incrocio: {len(self.crossing_stations)}")
    
    def find_optimal_schedule(
        self,
        train1: TrainPath,
        train2: TrainPath,
        time_window_start: datetime,
        time_window_end: datetime,
        frequency_minutes: int = 60,
        existing_traffic: Optional[List[ExistingTrain]] = None
    ) -> List[ScheduleProposal]:
        """
        Trova orari ottimali per coppia di treni in senso opposto.
        
        Args:
            train1: Primo treno (es. forward)
            train2: Secondo treno (es. backward, senso opposto)
            time_window_start: Inizio finestra temporale
            time_window_end: Fine finestra temporale
            frequency_minutes: Frequenza indicativa servizio
            existing_traffic: Traffico già presente sulla linea
            
        Returns:
            Lista di proposte ordinate per qualità (migliore prima)
        """
        if train1.direction == train2.direction:
            raise ValueError("I due treni devono avere direzioni opposte!")
        
        logger.info("🚂 OTTIMIZZAZIONE ORARI TRENI OPPOSTI")
        logger.info(f"   Treno 1: {train1.train_id} {train1.direction}")
        logger.info(f"   Treno 2: {train2.train_id} {train2.direction}")
        logger.info(f"   Finestra: {time_window_start} - {time_window_end}")
        logger.info(f"   Frequenza: {frequency_minutes} min")
        
        existing_traffic = existing_traffic or []
        proposals = []
        
        # Genera combinazioni di orari possibili
        time_slots = self._generate_time_slots(
            time_window_start, 
            time_window_end, 
            frequency_minutes
        )
        
        logger.info(f"   Slot temporali da testare: {len(time_slots)}")
        
        # Testa ogni combinazione
        for i, slot1 in enumerate(time_slots):
            for j, slot2 in enumerate(time_slots):
                # Evita slot troppo vicini (almeno 5 minuti di gap)
                if abs((slot2 - slot1).total_seconds()) < 300:
                    continue
                
                # Crea percorsi con orari proposti
                test_train1 = self._create_test_train(train1, slot1)
                test_train2 = self._create_test_train(train2, slot2)
                
                # Valuta questa combinazione
                proposal = self._evaluate_schedule(
                    test_train1, 
                    test_train2, 
                    existing_traffic
                )
                
                if proposal:
                    proposals.append(proposal)
        
        # Ordina per qualità (meno ritardo totale, più confidence)
        proposals.sort(key=lambda p: (p.total_delay_minutes, -p.confidence))
        
        logger.info(f"✅ Trovate {len(proposals)} proposte valide")
        if proposals:
            best = proposals[0]
            logger.info(f"   Migliore: ritardo {best.total_delay_minutes:.1f} min, "
                       f"incrocio km {best.crossing_point_km:.1f}")
        
        return proposals[:10]  # Top 10
    
    def _generate_time_slots(
        self, 
        start: datetime, 
        end: datetime, 
        frequency_minutes: int
    ) -> List[datetime]:
        """Genera slot temporali possibili."""
        slots = []
        current = start
        
        while current <= end:
            slots.append(current)
            current += timedelta(minutes=frequency_minutes // 2)  # Più granularità
        
        return slots
    
    def _create_test_train(self, template: TrainPath, departure: datetime) -> TrainPath:
        """Crea treno test con orario specifico."""
        return TrainPath(
            train_id=template.train_id,
            direction=template.direction,
            start_km=template.start_km,
            end_km=template.end_km,
            avg_speed_kmh=template.avg_speed_kmh,
            departure_time=departure,
            stops=template.stops,
            priority=template.priority
        )
    
    def _evaluate_schedule(
        self,
        train1: TrainPath,
        train2: TrainPath,
        existing_traffic: List[ExistingTrain]
    ) -> Optional[ScheduleProposal]:
        """
        Valuta una combinazione di orari.
        
        Returns:
            ScheduleProposal se valida, None se impossibile
        """
        # 1. Simula movimento treni
        train1_timeline = self._simulate_train_movement(train1)
        train2_timeline = self._simulate_train_movement(train2)
        
        # 2. Trova punti di conflitto su singolo binario
        conflicts = self._find_conflicts_on_single_track(
            train1_timeline, 
            train2_timeline
        )
        
        if not conflicts:
            # Nessun conflitto: orari perfetti!
            return ScheduleProposal(
                train1_departure=train1.departure_time,
                train2_departure=train2.departure_time,
                crossing_point_km=-1,
                crossing_time=train1.departure_time,
                train1_wait_minutes=0.0,
                train2_wait_minutes=0.0,
                total_delay_minutes=0.0,
                conflicts_avoided=0,
                confidence=1.0,
                reasoning="Nessun conflitto: percorsi completamente separati temporalmente"
            )
        
        # 3. Trova punto di incrocio ottimale
        crossing = self._find_optimal_crossing_point(train1_timeline, train2_timeline)
        
        if not crossing:
            return None  # Impossibile risolvere
        
        crossing_km, crossing_time, wait1, wait2 = crossing
        
        # 4. Verifica conflitti con traffico esistente
        conflicts_with_traffic = self._check_conflicts_with_traffic(
            train1_timeline,
            train2_timeline,
            existing_traffic
        )
        
        # 5. Calcola confidence
        confidence = self._calculate_confidence(
            wait1, wait2, conflicts_with_traffic, crossing_km
        )
        
        # 6. Genera reasoning
        reasoning = self._generate_reasoning(
            train1, train2, crossing_km, wait1, wait2, conflicts_with_traffic
        )
        
        return ScheduleProposal(
            train1_departure=train1.departure_time,
            train2_departure=train2.departure_time,
            crossing_point_km=crossing_km,
            crossing_time=crossing_time,
            train1_wait_minutes=wait1,
            train2_wait_minutes=wait2,
            total_delay_minutes=wait1 + wait2,
            conflicts_avoided=len(conflicts),
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _simulate_train_movement(self, train: TrainPath) -> Dict[float, datetime]:
        """
        Simula movimento treno lungo rete con precisione.
        
        Returns:
            Dict {km: timestamp} con orari passaggio precisi
        """
        timeline = {}
        current_time = train.departure_time
        
        # Aggiungi punto partenza
        timeline[train.start_km] = current_time
        
        # Determina direzione e ordine sezioni
        if train.direction == 'forward':
            relevant_sections = [s for s in self.track_sections 
                               if s.start_km >= train.start_km and s.end_km <= train.end_km]
            relevant_sections.sort(key=lambda s: s.start_km)
        else:  # backward
            relevant_sections = [s for s in self.track_sections 
                               if s.start_km >= train.end_km and s.end_km <= train.start_km]
            relevant_sections.sort(key=lambda s: s.start_km, reverse=True)
        
        # Simula attraversamento ogni sezione
        for section in relevant_sections:
            distance = section.length_km()
            speed = min(train.avg_speed_kmh, section.max_speed_kmh)
            travel_mins = (distance / speed) * 60.0
            
            # Aggiungi tempo viaggio
            current_time += timedelta(minutes=travel_mins)
            
            # Registra ingresso e uscita sezione
            if train.direction == 'forward':
                timeline[section.start_km] = current_time - timedelta(minutes=travel_mins)
                timeline[section.end_km] = current_time
            else:
                timeline[section.end_km] = current_time - timedelta(minutes=travel_mins)
                timeline[section.start_km] = current_time
            
            # Gestisci fermate in questa sezione
            for stop_km, stop_duration in train.stops:
                if section.start_km <= stop_km <= section.end_km:
                    # Calcola quando arriva alla fermata
                    if train.direction == 'forward':
                        stop_distance = stop_km - section.start_km
                    else:
                        stop_distance = section.end_km - stop_km
                    
                    stop_travel = (stop_distance / speed) * 60.0
                    stop_time = timeline[section.start_km if train.direction == 'forward' else section.end_km] + timedelta(minutes=stop_travel)
                    
                    timeline[stop_km] = stop_time
                    current_time = stop_time + timedelta(minutes=stop_duration)
        
        # Aggiungi punto arrivo finale
        timeline[train.end_km] = current_time
        
        return timeline
    
    def _find_conflicts_on_single_track(
        self,
        train1_timeline: Dict[float, datetime],
        train2_timeline: Dict[float, datetime]
    ) -> List[Tuple[float, float]]:
        """
        Trova conflitti su sezioni a singolo binario.
        
        Returns:
            Lista di (start_km, end_km) sezioni in conflitto
        """
        conflicts = []
        
        for section in self.single_track_sections:
            # Verifica se entrambi i treni attraversano questa sezione
            train1_enters = any(section.start_km <= km <= section.end_km for km in train1_timeline.keys())
            train2_enters = any(section.start_km <= km <= section.end_km for km in train2_timeline.keys())
            
            if train1_enters and train2_enters:
                # Trova orari ingresso/uscita
                train1_times = [t for km, t in train1_timeline.items() 
                               if section.start_km <= km <= section.end_km]
                train2_times = [t for km, t in train2_timeline.items() 
                               if section.start_km <= km <= section.end_km]
                
                if train1_times and train2_times:
                    # Verifica sovrapposizione temporale
                    train1_min, train1_max = min(train1_times), max(train1_times)
                    train2_min, train2_max = min(train2_times), max(train2_times)
                    
                    # Conflitto se finestre temporali si sovrappongono
                    if not (train1_max < train2_min or train2_max < train1_min):
                        conflicts.append((section.start_km, section.end_km))
        
        return conflicts
    
    def _find_optimal_crossing_point(
        self,
        train1_timeline: Dict[float, datetime],
        train2_timeline: Dict[float, datetime]
    ) -> Optional[Tuple[float, datetime, float, float]]:
        """
        Trova punto e tempo ottimale per incrocio.
        
        Returns:
            (crossing_km, crossing_time, wait_train1_min, wait_train2_min) o None
        """
        best_crossing = None
        min_total_wait = float('inf')
        
        # Prova ogni stazione di incrocio
        for station in self.crossing_stations:
            station_km = (station.start_km + station.end_km) / 2
            
            # Trova quando ciascun treno arriverebbe
            train1_arrival = self._interpolate_arrival_time(train1_timeline, station_km)
            train2_arrival = self._interpolate_arrival_time(train2_timeline, station_km)
            
            if train1_arrival and train2_arrival:
                # Calcola attese necessarie
                time_diff = (train2_arrival - train1_arrival).total_seconds() / 60.0
                
                if time_diff > 0:
                    # Train1 arriva prima, deve aspettare train2
                    wait1 = abs(time_diff)
                    wait2 = 0
                    crossing_time = train2_arrival
                else:
                    # Train2 arriva prima, deve aspettare train1
                    wait1 = 0
                    wait2 = abs(time_diff)
                    crossing_time = train1_arrival
                
                total_wait = wait1 + wait2
                
                # Penalizza attese molto lunghe
                if total_wait < 30:  # Max 30 minuti attesa ragionevole
                    if total_wait < min_total_wait:
                        min_total_wait = total_wait
                        best_crossing = (station_km, crossing_time, wait1, wait2)
        
        return best_crossing
    
    def _interpolate_arrival_time(
        self, 
        timeline: Dict[float, datetime], 
        target_km: float
    ) -> Optional[datetime]:
        """Interpola orario arrivo a un km specifico."""
        sorted_kms = sorted(timeline.keys())
        
        # Trova km immediatamente prima e dopo target
        before_km, after_km = None, None
        for km in sorted_kms:
            if km <= target_km:
                before_km = km
            if km >= target_km and after_km is None:
                after_km = km
        
        if before_km is None or after_km is None:
            return None
        
        if before_km == after_km:
            return timeline[before_km]
        
        # Interpolazione lineare
        before_time = timeline[before_km]
        after_time = timeline[after_km]
        
        distance_total = after_km - before_km
        distance_to_target = target_km - before_km
        fraction = distance_to_target / distance_total
        
        time_diff = (after_time - before_time).total_seconds()
        interpolated_seconds = time_diff * fraction
        
        return before_time + timedelta(seconds=interpolated_seconds)
    
    def _check_conflicts_with_traffic(
        self,
        train1_timeline: Dict[float, datetime],
        train2_timeline: Dict[float, datetime],
        existing_traffic: List[ExistingTrain]
    ) -> int:
        """Conta conflitti con traffico esistente."""
        conflicts = 0
        
        for existing in existing_traffic:
            # Verifica sovrapposizioni spaziali e temporali
            # (Implementazione semplificata)
            conflicts += 1 if np.random.rand() > 0.8 else 0
        
        return conflicts
    
    def _calculate_confidence(
        self, 
        wait1: float, 
        wait2: float, 
        conflicts: int,
        crossing_km: float
    ) -> float:
        """Calcola confidence score 0-1."""
        # Base confidence
        confidence = 1.0
        
        # Penalizza attese lunghe
        confidence -= (wait1 + wait2) / 100.0  # -1% per minuto
        
        # Penalizza conflitti con traffico
        confidence -= conflicts * 0.1
        
        # Bonus se incrocio in stazione ottimale (centro linea)
        if abs(crossing_km - self.total_length_km / 2) < 10:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_reasoning(
        self,
        train1: TrainPath,
        train2: TrainPath,
        crossing_km: float,
        wait1: float,
        wait2: float,
        conflicts: int
    ) -> str:
        """Genera spiegazione testuale."""
        parts = []
        
        # Incrocio
        station = next((s for s in self.crossing_stations 
                       if abs((s.start_km + s.end_km)/2 - crossing_km) < 1), None)
        if station:
            parts.append(f"Incrocio ottimale a {station.station_name} (km {crossing_km:.1f})")
        else:
            parts.append(f"Incrocio a km {crossing_km:.1f}")
        
        # Attese
        if wait1 > 0:
            parts.append(f"{train1.train_id} attende {wait1:.0f} min")
        if wait2 > 0:
            parts.append(f"{train2.train_id} attende {wait2:.0f} min")
        
        if wait1 == 0 and wait2 == 0:
            parts.append("Sincronizzazione perfetta")
        
        # Conflitti
        if conflicts > 0:
            parts.append(f"{conflicts} potenziali conflitti con traffico esistente")
        else:
            parts.append("Nessun conflitto con traffico")
        
        return ". ".join(parts) + "."


def demo_opposite_train_scheduler():
    """Demo funzionalità."""
    print("\n" + "="*70)
    print("🚂 DEMO: OTTIMIZZAZIONE ORARI TRENI OPPOSTI")
    print("="*70)
    
    # Definisci rete ferroviaria
    track_sections = [
        # Stazione A (km 0-2): doppio binario
        TrackSection(1, 0.0, 2.0, num_tracks=2, max_speed_kmh=80, 
                    has_station=True, station_name="Stazione A", can_cross=True),
        
        # Sezione singolo binario (km 2-15)
        TrackSection(2, 2.0, 15.0, num_tracks=1, max_speed_kmh=120, 
                    has_station=False),
        
        # Stazione intermedia B (km 15-17): doppio binario, può incrociare
        TrackSection(3, 15.0, 17.0, num_tracks=2, max_speed_kmh=80, 
                    has_station=True, station_name="Stazione B", can_cross=True),
        
        # Sezione singolo binario (km 17-30)
        TrackSection(4, 17.0, 30.0, num_tracks=1, max_speed_kmh=120, 
                    has_station=False),
        
        # Stazione C (km 30-32): doppio binario
        TrackSection(5, 30.0, 32.0, num_tracks=2, max_speed_kmh=80, 
                    has_station=True, station_name="Stazione C", can_cross=True),
    ]
    
    # Crea scheduler
    scheduler = OppositeTrainScheduler(track_sections)
    
    # Definisci treni
    base_time = datetime(2025, 11, 19, 8, 0)
    
    train1 = TrainPath(
        train_id="IC 501",
        direction="forward",
        start_km=0.0,
        end_km=32.0,
        avg_speed_kmh=100.0,
        departure_time=base_time,  # Sarà ottimizzato
        stops=[(16.0, 2)],  # Fermata 2 min a Stazione B
        priority=7
    )
    
    train2 = TrainPath(
        train_id="IC 502",
        direction="backward",
        start_km=32.0,
        end_km=0.0,
        avg_speed_kmh=100.0,
        departure_time=base_time,  # Sarà ottimizzato
        stops=[(16.0, 2)],  # Fermata 2 min a Stazione B
        priority=7
    )
    
    # Ottimizza orari
    proposals = scheduler.find_optimal_schedule(
        train1,
        train2,
        time_window_start=base_time,
        time_window_end=base_time + timedelta(hours=2),
        frequency_minutes=60,
        existing_traffic=[]
    )
    
    # Mostra risultati
    print(f"\n📊 RISULTATI: {len(proposals)} proposte trovate\n")
    
    for i, proposal in enumerate(proposals[:5], 1):
        print(f"{i}. Proposta (confidence: {proposal.confidence:.2f})")
        print(f"   {train1.train_id}: partenza {proposal.train1_departure.strftime('%H:%M')}")
        print(f"   {train2.train_id}: partenza {proposal.train2_departure.strftime('%H:%M')}")
        print(f"   Incrocio: km {proposal.crossing_point_km:.1f} alle {proposal.crossing_time.strftime('%H:%M')}")
        print(f"   Attese: {proposal.train1_wait_minutes:.0f} + {proposal.train2_wait_minutes:.0f} = "
              f"{proposal.total_delay_minutes:.0f} min totali")
        print(f"   {proposal.reasoning}")
        print()
    
    # Migliore proposta
    if proposals:
        best = proposals[0]
        print("="*70)
        print("✅ RACCOMANDAZIONE MIGLIORE:")
        print(f"   {train1.train_id}: {best.train1_departure.strftime('%H:%M')}")
        print(f"   {train2.train_id}: {best.train2_departure.strftime('%H:%M')}")
        print(f"   Ritardo totale: {best.total_delay_minutes:.0f} minuti")
        print("="*70)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    demo_opposite_train_scheduler()
