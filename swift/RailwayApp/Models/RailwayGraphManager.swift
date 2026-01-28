import Foundation

// MARK: - Data Models

/// Rappresenta una stazione della rete ferroviaria.
public struct Station: Codable, Identifiable {
    public let id: Int
    public let name: String
    public let numPlatforms: Int
    public let lat: Double?
    public let lon: Double?
    
    enum CodingKeys: String, CodingKey {
        case id, name, lat, lon
        case numPlatforms = "num_platforms"
    }
}

/// Rappresenta un binario (track) che collega due stazioni.
public struct Track: Codable, Identifiable {
    public let id: Int
    public let lengthKm: Double
    public let isSingleTrack: Bool
    public let capacity: Int
    public let stationIds: [Int]
    
    enum CodingKeys: String, CodingKey {
        case id
        case lengthKm = "length_km"
        case isSingleTrack = "is_single_track"
        case capacity
        case stationIds = "station_ids"
    }
}

/// Rappresenta lo stato corrente di un treno.
public struct Train: Codable, Identifiable {
    public let id: Int
    public var originStationId: Int
    public var destinationStationId: Int
    public var scheduledDepartureTime: String // Formato HH:MM:SS
    public var velocityKmh: Double
    public var positionKm: Double
    public var currentTrackId: Int
    public var priority: Int = 5
    public var isDelayed: Bool = false
    public var delayMinutes: Double = 0.0
    public var plannedRoute: [Int]? // Array di Track IDs opzionale
    
    enum CodingKeys: String, CodingKey {
        case id
        case originStationId = "origin_station"
        case destinationStationId = "destination_station"
        case scheduledDepartureTime = "scheduled_departure_time"
        case velocityKmh = "velocity_kmh"
        case positionKm = "position_km"
        case currentTrackId = "current_track"
        case priority
        case isDelayed = "is_delayed"
        case delayMinutes = "delay_minutes"
        case plannedRoute = "planned_route"
    }
}

// MARK: - AI Request/Response Models

struct AIRequestPayload: Codable {
    let trains: [Train]
    let stations: [Station]
    let tracks: [Track]
    let maxIterations: Int
    let gaMaxIterations: Int
    let gaPopulationSize: Int
    
    enum CodingKeys: String, CodingKey {
        case trains, stations, tracks
        case maxIterations = "max_iterations"
        case gaMaxIterations = "ga_max_iterations"
        case gaPopulationSize = "ga_population_size"
    }
}

// MARK: - Railway Graph Manager

public class RailwayGraphManager {
    
    public static let shared = RailwayGraphManager()
    
    public private(set) var stations: [Station] = []
    public private(set) var tracks: [Track] = []
    
    // Mappa di adiacenza per navigazione rapida: StationID -> [Track]
    private var adjacencyList: [Int: [Track]] = [:]
    
    private init() {}
    
    /// Carica la rete ferroviaria da un file JSON (formato RailwayAI).
    /// - Parameter jsonData: Il contenuto del file JSON (es. toscana_cleaned.json)
    public func loadNetwork(fromJsonData jsonData: Data) throws {
        // Struttura temporanea per il parsing del file intero scollegato
        struct NetworkFile: Codable {
            let stations: [Station]
            let tracks: [Track]
        }
        
        let decoder = JSONDecoder()
        let network = try decoder.decode(NetworkFile.self, from: jsonData)
        
        self.stations = network.stations
        self.tracks = network.tracks
        
        self.buildGraph()
        print("RailwayGraphManager: Caricate \(stations.count) stazioni e \(tracks.count) binari.")
    }
    
    /// Costruisce la mappa di adiacenza per il grafo.
    private func buildGraph() {
        self.adjacencyList.removeAll()
        
        for track in tracks {
            // Ogni track collega due stazioni (stationIds[0] e stationIds[1])
            if track.stationIds.count >= 2 {
                let s1 = track.stationIds[0]
                let s2 = track.stationIds[1]
                
                // Aggiungi connessione per s1
                if adjacencyList[s1] == nil { adjacencyList[s1] = [] }
                adjacencyList[s1]?.append(track)
                
                // Aggiungi connessione per s2
                if adjacencyList[s2] == nil { adjacencyList[s2] = [] }
                adjacencyList[s2]?.append(track)
            }
        }
    }
    
    /// Genera il JSON Payload pronto per essere inviato all'endpoint AI `/api/v1/optimize`.
    /// - Parameters:
    ///   - activeTrains: La lista dei treni attualmente attivi simulati dalla App.
    ///   - maxIterations: Orizzonte di simulazione (default 100 minuti).
    /// - Returns: Una stringa JSON formattata o nil in caso di errore.
    public func generateAIRequestJSON(for activeTrains: [Train], maxIterations: Int = 100) -> String? {
        
        // Costruiamo il payload completo come richiesto dal server Python
        let payload = AIRequestPayload(
            trains: activeTrains,
            stations: self.stations,
            tracks: self.tracks,
            maxIterations: maxIterations,
            gaMaxIterations: 300,  // Valori ottimizzati per reti grandi
            gaPopulationSize: 100
        )
        
        let encoder = JSONEncoder()
        encoder.outputFormatting = .prettyPrinted // Opzionale, per debug
        
        do {
            let data = try encoder.encode(payload)
            return String(data: data, encoding: .utf8)
        } catch {
            print("RailwayGraphManager Error: Impossibile serializzare richiesta AI - \(error)")
            return nil
        }
    }
    
    // MARK: - Utility Methods per la App
    
    /// Trova i binari connessi a una stazione specifica.
    public func getTracks(connectedTo stationId: Int) -> [Track] {
        return adjacencyList[stationId] ?? []
    }
    
    public func getStation(byId id: Int) -> Station? {
        return stations.first(where: { $0.id == id })
    }
    
    public func getTrack(byId id: Int) -> Track? {
        return tracks.first(where: { $0.id == id })
    }
}
