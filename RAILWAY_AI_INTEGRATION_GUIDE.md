---
title: Railway AI Integration Guide
description: Guida completa per integrare Railway AI nell'applicazione Swift
version: 1.0
date: 2026-02-03
---

# Railway AI Integration Guide

Questa guida spiega come modificare l'applicazione Swift per utilizzare il backend Railway AI per l'ottimizzazione degli orari ferroviari.

## 📋 Indice

1. [Panoramica del Sistema](#panoramica-del-sistema)
2. [Configurazione Base](#configurazione-base)
3. [Autenticazione](#autenticazione)
4. [Integrazione API](#integrazione-api)
5. [Gestione Scenari](#gestione-scenari)
6. [Ottimizzazione Orari](#ottimizzazione-orari)
7. [Monitoring in Tempo Reale](#monitoring-in-tempo-reale)
8. [Best Practices](#best-practices)

---

## 🎯 Panoramica del Sistema

Railway AI è un backend FastAPI che fornisce:
- **Ottimizzazione AI** degli orari ferroviari tramite MARL (Multi-Agent Reinforcement Learning)
- **Generazione automatica** di scenari da OpenStreetMap
- **Training continuo** del modello in background
- **API RESTful** per integrazione con client esterni
- **WebSocket** per aggiornamenti in tempo reale

**Endpoint Base**: `https://railway-ai.michelebigi.it`

---

## ⚙️ Configurazione Base

### 1. Aggiorna `AppConfig.swift`

```swift
import Foundation

struct AppConfig {
    // Railway AI Backend
    static let railwayAIBaseURL = "https://railway-ai.michelebigi.it"
    
    // Endpoints
    static let authEndpoint = "\(railwayAIBaseURL)/token"
    static let optimizeEndpoint = "\(railwayAIBaseURL)/api/v1/optimize"
    static let scenarioEndpoint = "\(railwayAIBaseURL)/api/v1/scenario/generate"
    static let metricsEndpoint = "\(railwayAIBaseURL)/api/v1/metrics"
    static let modelInfoEndpoint = "\(railwayAIBaseURL)/api/v1/model/info"
    
    // WebSocket
    static let monitoringWSURL = "wss://railway-ai.michelebigi.it/ws/monitoring"
    
    // Timeout
    static let requestTimeout: TimeInterval = 30.0
    static let optimizationTimeout: TimeInterval = 120.0
}
```

### 2. Crea `RailwayAIService.swift`

```swift
import Foundation
import Combine

class RailwayAIService: ObservableObject {
    @Published var isAuthenticated = false
    @Published var apiKey: String?
    @Published var lastError: String?
    
    private var cancellables = Set<AnyCancellable>()
    
    // Singleton
    static let shared = RailwayAIService()
    
    private init() {
        // Carica API Key salvata
        loadSavedCredentials()
    }
    
    // MARK: - Authentication
    
    func login(username: String, password: String) async throws {
        let url = URL(string: AppConfig.authEndpoint)!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        
        let body = "username=\(username)&password=\(password)"
        request.httpBody = body.data(using: .utf8)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw RailwayAIError.authenticationFailed
        }
        
        let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)
        
        await MainActor.run {
            self.apiKey = tokenResponse.access_token
            self.isAuthenticated = true
        }
        
        // Salva credenziali
        saveCredentials(apiKey: tokenResponse.access_token)
    }
    
    func logout() {
        apiKey = nil
        isAuthenticated = false
        clearSavedCredentials()
    }
    
    // MARK: - Optimization
    
    func optimizeSchedule(
        trains: [Train],
        tracks: [Track],
        stations: [Station]
    ) async throws -> OptimizationResult {
        guard let apiKey = apiKey else {
            throw RailwayAIError.notAuthenticated
        }
        
        let url = URL(string: AppConfig.optimizeEndpoint)!
        var request = URLRequest(url: url, timeoutInterval: AppConfig.optimizationTimeout)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        
        let requestBody = OptimizationRequest(
            trains: trains.map { $0.toDTO() },
            tracks: tracks.map { $0.toDTO() },
            stations: stations.map { $0.toDTO() }
        )
        
        request.httpBody = try JSONEncoder().encode(requestBody)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw RailwayAIError.invalidResponse
        }
        
        if httpResponse.statusCode == 401 {
            await MainActor.run { self.isAuthenticated = false }
            throw RailwayAIError.authenticationFailed
        }
        
        guard httpResponse.statusCode == 200 else {
            throw RailwayAIError.optimizationFailed(statusCode: httpResponse.statusCode)
        }
        
        return try JSONDecoder().decode(OptimizationResult.self, from: data)
    }
    
    // MARK: - Scenario Generation
    
    func generateScenario(area: String) async throws -> String {
        guard let apiKey = apiKey else {
            throw RailwayAIError.notAuthenticated
        }
        
        let url = URL(string: AppConfig.scenarioEndpoint)!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        
        let body = ["area": area]
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw RailwayAIError.scenarioGenerationFailed
        }
        
        let result = try JSONDecoder().decode(ScenarioResponse.self, from: data)
        return result.scenario_path
    }
    
    // MARK: - Metrics
    
    func fetchMetrics() async throws -> AIMetrics {
        let url = URL(string: AppConfig.metricsEndpoint)!
        var request = URLRequest(url: url)
        request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(AIMetrics.self, from: data)
    }
    
    // MARK: - Persistence
    
    private func saveCredentials(apiKey: String) {
        UserDefaults.standard.set(apiKey, forKey: "railway_ai_api_key")
    }
    
    private func loadSavedCredentials() {
        if let savedKey = UserDefaults.standard.string(forKey: "railway_ai_api_key") {
            self.apiKey = savedKey
            self.isAuthenticated = true
        }
    }
    
    private func clearSavedCredentials() {
        UserDefaults.standard.removeObject(forKey: "railway_ai_api_key")
    }
}

// MARK: - Data Models

struct TokenResponse: Codable {
    let access_token: String
    let token_type: String
}

struct OptimizationRequest: Codable {
    let trains: [TrainDTO]
    let tracks: [TrackDTO]
    let stations: [StationDTO]
}

struct OptimizationResult: Codable {
    let optimized_schedules: [OptimizedSchedule]
    let conflicts_resolved: Int
    let total_delay_minutes: Double
    let efficiency_score: Double
}

struct OptimizedSchedule: Codable {
    let train_id: String
    let departure_time: String
    let arrival_time: String
    let platform: String?
    let route: [String]
}

struct ScenarioResponse: Codable {
    let scenario_path: String
    let stations_count: Int
    let tracks_count: Int
}

struct AIMetrics: Codable {
    let total_requests: Int
    let successful_optimizations: Int
    let failed_optimizations: Int
    let avg_inference_time_ms: Double
}

enum RailwayAIError: LocalizedError {
    case notAuthenticated
    case authenticationFailed
    case invalidResponse
    case optimizationFailed(statusCode: Int)
    case scenarioGenerationFailed
    case networkError(Error)
    
    var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "Non autenticato. Effettua il login."
        case .authenticationFailed:
            return "Autenticazione fallita. Verifica le credenziali."
        case .invalidResponse:
            return "Risposta del server non valida."
        case .optimizationFailed(let code):
            return "Ottimizzazione fallita (HTTP \(code))."
        case .scenarioGenerationFailed:
            return "Generazione scenario fallita."
        case .networkError(let error):
            return "Errore di rete: \(error.localizedDescription)"
        }
    }
}
```

### 3. Estendi i Modelli Esistenti

Aggiungi metodi `toDTO()` ai tuoi modelli per convertirli nel formato richiesto dall'API:

```swift
extension Train {
    func toDTO() -> TrainDTO {
        TrainDTO(
            id: self.id.uuidString,
            name: self.name,
            type: self.type.rawValue,
            route: self.itinerary.map { $0.station.id.uuidString },
            departure_time: self.departureTime.ISO8601Format(),
            arrival_time: self.arrivalTime.ISO8601Format()
        )
    }
}

extension Track {
    func toDTO() -> TrackDTO {
        TrackDTO(
            id: self.id.uuidString,
            from_station: self.fromStation.id.uuidString,
            to_station: self.toStation.id.uuidString,
            distance_km: self.distance,
            max_speed_kmh: self.maxSpeed
        )
    }
}

extension Station {
    func toDTO() -> StationDTO {
        StationDTO(
            id: self.id.uuidString,
            name: self.name,
            latitude: self.coordinate.latitude,
            longitude: self.coordinate.longitude,
            platforms: self.platforms
        )
    }
}

struct TrainDTO: Codable {
    let id: String
    let name: String
    let type: String
    let route: [String]
    let departure_time: String
    let arrival_time: String
}

struct TrackDTO: Codable {
    let id: String
    let from_station: String
    let to_station: String
    let distance_km: Double
    let max_speed_kmh: Double
}

struct StationDTO: Codable {
    let id: String
    let name: String
    let latitude: Double
    let longitude: Double
    let platforms: Int
}
```

---

## 🔐 Autenticazione

### Login View

```swift
struct RailwayAILoginView: View {
    @StateObject private var aiService = RailwayAIService.shared
    @State private var username = ""
    @State private var password = ""
    @State private var isLoading = false
    @State private var errorMessage: String?
    
    var body: some View {
        Form {
            Section("Railway AI Credentials") {
                TextField("Username", text: $username)
                    .textContentType(.username)
                    .autocapitalization(.none)
                
                SecureField("Password", text: $password)
                    .textContentType(.password)
            }
            
            if let error = errorMessage {
                Section {
                    Text(error)
                        .foregroundColor(.red)
                }
            }
            
            Section {
                Button(action: login) {
                    if isLoading {
                        ProgressView()
                    } else {
                        Text("Login")
                    }
                }
                .disabled(username.isEmpty || password.isEmpty || isLoading)
            }
        }
        .navigationTitle("Railway AI")
    }
    
    private func login() {
        isLoading = true
        errorMessage = nil
        
        Task {
            do {
                try await aiService.login(username: username, password: password)
            } catch {
                await MainActor.run {
                    errorMessage = error.localizedDescription
                }
            }
            await MainActor.run {
                isLoading = false
            }
        }
    }
}
```

---

## 🚀 Ottimizzazione Orari

### Integrazione nel ViewModel

```swift
class ScheduleViewModel: ObservableObject {
    @Published var trains: [Train] = []
    @Published var isOptimizing = false
    @Published var optimizationResult: OptimizationResult?
    
    private let aiService = RailwayAIService.shared
    private let graphManager: RailwayGraphManager
    
    func optimizeWithAI() {
        guard aiService.isAuthenticated else {
            // Mostra alert per login
            return
        }
        
        isOptimizing = true
        
        Task {
            do {
                let result = try await aiService.optimizeSchedule(
                    trains: trains,
                    tracks: graphManager.tracks,
                    stations: graphManager.stations
                )
                
                await MainActor.run {
                    self.optimizationResult = result
                    self.applyOptimization(result)
                    self.isOptimizing = false
                }
            } catch {
                await MainActor.run {
                    self.isOptimizing = false
                    // Mostra errore
                }
            }
        }
    }
    
    private func applyOptimization(_ result: OptimizationResult) {
        for schedule in result.optimized_schedules {
            if let train = trains.first(where: { $0.id.uuidString == schedule.train_id }) {
                // Aggiorna orari del treno
                train.departureTime = ISO8601DateFormatter().date(from: schedule.departure_time) ?? train.departureTime
                train.arrivalTime = ISO8601DateFormatter().date(from: schedule.arrival_time) ?? train.arrivalTime
                
                // Aggiorna binario se specificato
                if let platform = schedule.platform {
                    train.platform = platform
                }
            }
        }
    }
}
```

### UI Button

```swift
Button(action: { viewModel.optimizeWithAI() }) {
    Label("Ottimizza con AI", systemImage: "brain")
}
.disabled(!RailwayAIService.shared.isAuthenticated || viewModel.isOptimizing)
```

---

## 📊 Monitoring in Tempo Reale

### WebSocket Manager

```swift
import Foundation

class RailwayAIMonitor: ObservableObject {
    @Published var trainingUpdates: [TrainingUpdate] = []
    @Published var systemMetrics: SystemMetrics?
    
    private var webSocketTask: URLSessionWebSocketTask?
    
    func connect() {
        guard let url = URL(string: AppConfig.monitoringWSURL) else { return }
        
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        receiveMessage()
    }
    
    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleMessage(text)
                case .data(let data):
                    self?.handleData(data)
                @unknown default:
                    break
                }
                self?.receiveMessage() // Continue listening
                
            case .failure(let error):
                print("WebSocket error: \(error)")
            }
        }
    }
    
    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8) else { return }
        
        if let update = try? JSONDecoder().decode(WSMessage.self, from: data) {
            DispatchQueue.main.async {
                switch update.type {
                case "training_update":
                    // Handle training update
                    break
                case "state_update":
                    // Handle state update
                    break
                default:
                    break
                }
            }
        }
    }
}

struct WSMessage: Codable {
    let type: String
    let episode: Int?
    let reward: Double?
    let conflicts: Int?
}
```

---

## ✅ Best Practices

### 1. **Error Handling**
- Gestisci sempre errori di rete e timeout
- Mostra messaggi user-friendly
- Implementa retry logic per richieste fallite

### 2. **Caching**
- Salva risultati ottimizzazione localmente
- Cache metriche per ridurre chiamate API
- Usa `UserDefaults` per API Key

### 3. **Performance**
- Usa `async/await` per chiamate non bloccanti
- Mostra progress indicator durante ottimizzazione
- Limita dimensione dati inviati (max 1000 treni)

### 4. **Security**
- Non hardcodare credenziali
- Usa Keychain per API Key sensibili
- Valida sempre certificati SSL

### 5. **UX**
- Mostra stato connessione Railway AI
- Indica chiaramente quando AI è in uso
- Permetti fallback a ottimizzazione locale

---

## 🔧 Testing

### Unit Test

```swift
import XCTest

class RailwayAIServiceTests: XCTestCase {
    var service: RailwayAIService!
    
    override func setUp() {
        service = RailwayAIService.shared
    }
    
    func testAuthentication() async throws {
        try await service.login(username: "test", password: "test")
        XCTAssertTrue(service.isAuthenticated)
        XCTAssertNotNil(service.apiKey)
    }
    
    func testOptimization() async throws {
        // Setup test data
        let trains = createTestTrains()
        let tracks = createTestTracks()
        let stations = createTestStations()
        
        let result = try await service.optimizeSchedule(
            trains: trains,
            tracks: tracks,
            stations: stations
        )
        
        XCTAssertGreaterThan(result.optimized_schedules.count, 0)
        XCTAssertGreaterThanOrEqual(result.efficiency_score, 0)
    }
}
```

---

## 📞 Support

Per problemi o domande:
- **API Docs**: `https://railway-ai.michelebigi.it/docs`
- **Dashboard**: `https://railway-ai.michelebigi.it/static/index.html`
- **Logs**: Controlla la sezione "AI Management" nella dashboard

---

**Versione**: 1.0  
**Ultimo aggiornamento**: 2026-02-03
