
//
//  AppConfig.swift
//  RailwayApp
//
//  Centralized configuration for API endpoints.
//

import Foundation

public struct AppConfig {
    
    // Cambia questo valore in .local o .production a seconda di dove stai testando
    static let currentEnvironment: Environment = .local
    
    public enum Environment {
        case local
        case production
        case custom(String)
        
        var baseURL: String {
            switch self {
            case .local:
                // Se usi il Simulatore iOS, localhost va bene.
                // Se usi un DISPOSITIVO FISICO, metti qui l'IP del tuo Mac (es. "http://192.168.1.15:8000")
                return "http://localhost:8000"
            case .production:
                return "https://railway-ai.michelebigi.it"
            case .custom(let url):
                return url
            }
        }
    }
    
    static var apiBaseURL: String {
        return currentEnvironment.baseURL
    }
}
