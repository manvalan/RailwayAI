
//
//  ScheduleProposer.swift
//  RailwayApp
//
//  Manager for interacting with the Fast Schedule Proposal API.
//

import Foundation

// MARK: - Proposal Models

public struct ScheduleProposalRequest: Codable {
    let stations: [Station]
    let tracks: [Track]
    let targetLines: Int
    
    enum CodingKeys: String, CodingKey {
        case stations, tracks
        case targetLines = "target_lines"
    }
}

public struct ProposedLine: Codable, Identifiable {
    public let id: String
    public let originId: Int
    public let destinationId: Int
    public let frequency: String
    public let firstDepartureMinute: Int
    
    enum CodingKeys: String, CodingKey {
        case id, frequency
        case originId = "origin"
        case destinationId = "destination"
        case firstDepartureMinute = "first_departure_minute"
    }
}

public struct SchedulePreviewItem: Codable, Identifiable {
    public var id: String { "\(line)-\(departure)" }
    public let line: String
    public let departure: String
    public let originId: Int
    public let destinationId: Int
    
    enum CodingKeys: String, CodingKey {
        case line, departure
        case originId = "origin"
        case destinationId = "destination"
    }
}

public struct ScheduleProposalResponse: Codable {
    public let success: Bool
    public let proposal: ProposalData
    public let meta: MetaData
    
    public struct ProposalData: Codable {
        public let proposedLines: [ProposedLine]
        public let schedulePreview: [SchedulePreviewItem]
        
        enum CodingKeys: String, CodingKey {
            case proposedLines = "proposed_lines"
            case schedulePreview = "schedule_preview"
        }
    }
    
    public struct MetaData: Codable {
        public let executionSpeed: String
        enum CodingKeys: String, CodingKey {
            case executionSpeed = "execution_speed"
        }
    }
}

// MARK: - Schedule Proposer Service

public class ScheduleProposer {
    public static let shared = ScheduleProposer()
    private let baseURL = AppConfig.apiBaseURL
    
    private init() {}
    
    /// Requests a fast schedule proposal from the AI based on current network graph.
    /// - Parameters:
    ///   - graph: The RailwayGraphManager instance containing map data.
    ///   - targetLines: How many train lines to suggest (default 5).
    public func requestProposal(
        using graph: RailwayGraphManager,
        targetLines: Int = 5,
        completion: @escaping (Result<ScheduleProposalResponse, Error>) -> Void
    ) {
        let endpoint = "\(baseURL)/api/v1/propose_schedule"
        var request = URLRequest(url: URL(string: endpoint)!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Add Auth Headers automatically
        AuthenticationManager.shared.attachAuthHeaders(to: &request)
        
        // Prepare Body
        let payload = ScheduleProposalRequest(
            stations: graph.stations,
            tracks: graph.tracks,
            targetLines: targetLines
        )
        
        do {
            request.httpBody = try JSONEncoder().encode(payload)
        } catch {
            completion(.failure(error))
            return
        }
        
        // Execute
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(AuthError.serverError("No data")))
                return
            }
            
            // Debug: print JSON response
            // if let str = String(data: data, encoding: .utf8) { print("AI Response: \(str)") }
            
            do {
                let responseObj = try JSONDecoder().decode(ScheduleProposalResponse.self, from: data)
                completion(.success(responseObj))
            } catch {
                print("Decoding error: \(error)")
                completion(.failure(error))
            }
        }.resume()
    }
}
