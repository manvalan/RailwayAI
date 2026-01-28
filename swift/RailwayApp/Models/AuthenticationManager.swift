
//
//  AuthenticationManager.swift
//  RailwayApp
//
//  Created for RailwayAI Agent Integration.
//

import Foundation
import Combine

public enum AuthError: Error {
    case invalidCredentials
    case serverError(String)
    case decodingError
    case missingToken
    case inactiveAccount // Handles code 403 "Account is inactive"
}

public class AuthenticationManager {
    public static let shared = AuthenticationManager()
    
    // Configuration
    private let baseURL = AppConfig.apiBaseURL
    private var apiKey: String?
    private var jwtToken: String?
    
    private init() {}
    
    /// Checks if we have valid credentials
    public var isAuthenticated: Bool {
        return apiKey != nil || jwtToken != nil
    }
    
    /// Sets a permanent API Key manually (if already obtained).
    public func setAPIKey(_ key: String) {
        self.apiKey = key
        print("AuthManager: API Key set manually.")
    }
    
    // MARK: - Login Flow
    
    /// Logs in using username/password to get a temporary JWT token.
    public func login(username: String, password: String, completion: @escaping (Result<String, AuthError>) -> Void) {
        let endpoint = "\(baseURL)/token"
        var request = URLRequest(url: URL(string: endpoint)!)
        request.httpMethod = "POST"
        
        // OAuth2 Password Request Body (form-urlencoded)
        let bodyString = "username=\(username)&password=\(password)"
        request.httpBody = bodyString.data(using: .utf8)
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let data = data, error == nil else {
                completion(.failure(.serverError(error?.localizedDescription ?? "Unknown error")))
                return
            }
            
            if let httpResponse = response as? HTTPURLResponse {
                if httpResponse.statusCode == 403 {
                    completion(.failure(.inactiveAccount))
                    return
                }
                if httpResponse.statusCode != 200 {
                    completion(.failure(.invalidCredentials))
                    return
                }
            }
            
            // Decode Token
            struct TokenResponse: Decodable {
                let access_token: String
                let token_type: String
            }
            
            do {
                let tokenObj = try JSONDecoder().decode(TokenResponse.self, from: data)
                self?.jwtToken = tokenObj.access_token
                print("AuthManager: Login successful. JWT Token obtained.")
                completion(.success(tokenObj.access_token))
            } catch {
                completion(.failure(.decodingError))
            }
        }.resume()
    }
    
    // MARK: - API Key Generation Flow
    
    /// Generates a permanent API Key. Requires prior login (JWT).
    public func generatePermanentKey(completion: @escaping (Result<String, AuthError>) -> Void) {
        guard let token = self.jwtToken else {
            completion(.failure(.missingToken))
            return
        }
        
        let endpoint = "\(baseURL)/api/v1/generate-key"
        var request = URLRequest(url: URL(string: endpoint)!)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let data = data, error == nil else {
                completion(.failure(.serverError(error?.localizedDescription ?? "Network error")))
                return
            }
            
            struct KeyResponse: Decodable {
                let api_key: String
            }
            
            do {
                let keyObj = try JSONDecoder().decode(KeyResponse.self, from: data)
                self?.apiKey = keyObj.api_key
                print("AuthManager: Permanent API Key Generated: \(keyObj.api_key)")
                completion(.success(keyObj.api_key))
            } catch {
                completion(.failure(.decodingError))
            }
        }.resume()
    }
    
    // MARK: - Registration Flow (Admin)
    
    /// Registers a new user. Requires Admin authentication.
    public func registerNewUser(username: String, password: String, completion: @escaping (Result<Bool, AuthError>) -> Void) {
        let endpoint = "\(baseURL)/api/v1/register"
        var request = URLRequest(url: URL(string: endpoint)!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Admin Auth (Either API Key or Token)
        if let key = apiKey {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
        } else if let token = jwtToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        let body: [String: String] = ["username": username, "password": password]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                completion(.success(true))
            } else {
                completion(.failure(.serverError("Registration failed")))
            }
        }.resume()
    }
    
    /// Helper to attach headers to any request
    public func attachAuthHeaders(to request: inout URLRequest) {
        if let key = apiKey {
            request.setValue(key, forHTTPHeaderField: "X-API-Key")
        } else if let token = jwtToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
    }
}
