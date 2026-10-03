import Foundation
import Security

enum SharedSettings {
    static let group = "group.com.example.AIUsageMac"
    static let defaultURL = "http://127.0.0.1:8787"
    static var defaults: UserDefaults? { UserDefaults(suiteName: group) }

    static var baseURL: String {
        defaults?.string(forKey: "baseURL") ?? defaultURL
    }

    static var keychainGroup: String? {
        Bundle.main.object(forInfoDictionaryKey: "AIUsageKeychainGroup") as? String
    }

    static func allowedURL(_ value: String) -> URL? {
        guard let url = URL(string: value.trimmingCharacters(in: .whitespacesAndNewlines)),
              let scheme = url.scheme?.lowercased(), let host = url.host?.lowercased(),
              (scheme == "https" || (scheme == "http" && ["localhost", "127.0.0.1", "::1"].contains(host)))
        else { return nil }
        return url
    }
}

enum APIKeyStore {
    private static let service = "com.example.AIUsageMac.api"
    private static let account = "local-monitor"

    private static func query() -> [String: Any] {
        var result: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        if let group = SharedSettings.keychainGroup, !group.isEmpty {
            result[kSecAttrAccessGroup as String] = group
        }
        return result
    }

    static func read() -> String? {
        var request = query()
        request[kSecReturnData as String] = true
        request[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        guard SecItemCopyMatching(request as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func save(_ value: String) throws {
        let key = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !key.isEmpty else { throw UsageError.invalidConfiguration }
        let request = query()
        SecItemDelete(request as CFDictionary)
        var add = request
        add[kSecValueData as String] = Data(key.utf8)
        add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        let status = SecItemAdd(add as CFDictionary, nil)
        guard status == errSecSuccess else { throw UsageError.keychain(status) }
    }
}

enum UsageError: LocalizedError {
    case invalidConfiguration
    case keychain(OSStatus)
    case badResponse

    var errorDescription: String? {
        switch self {
        case .invalidConfiguration: return "Isi URL lokal dan API key terlebih dahulu."
        case .keychain(let status): return "Keychain gagal menyimpan API key (\(status))."
        case .badResponse: return "API monitoring tidak memberikan respons yang valid."
        }
    }
}

struct ClaudeUsage: Codable {
    struct Meter: Codable {
        let pctActual: Double?
        let resetsAt: String?
        enum CodingKeys: String, CodingKey {
            case pctActual = "pct_actual", resetsAt = "reset_at"
        }
    }
    struct Projection: Codable {
        let status: String?
        let resetAt: String?
        let projectedPctAtReset: Double?
        let safeUntilReset: Bool?
        enum CodingKeys: String, CodingKey {
            case status, resetAt = "reset_at"
            case projectedPctAtReset = "projected_pct_at_reset"
            case safeUntilReset = "safe_until_reset"
        }
    }
    let weekly: Meter?
    let session: Meter?
    let projection: Projection?
}

struct ChatGPTUsage: Codable {
    struct Window: Codable {
        let label: String
        let usedPercent: Double?
        let resetAt: String?
        let windowHours: Double?
        enum CodingKeys: String, CodingKey {
            case label, usedPercent = "used_percent", resetAt = "reset_at"
            case windowHours = "window_hours"
        }
    }
    struct Projection: Codable {
        let label: String
        let status: String?
        let resetAt: String?
        let projectedPctAtReset: Double?
        let safeUntilReset: Bool?
        enum CodingKeys: String, CodingKey {
            case label, status, resetAt = "reset_at"
            case projectedPctAtReset = "projected_pct_at_reset"
            case safeUntilReset = "safe_until_reset"
        }
    }
    let windows: [Window]
    let projections: [Projection]

    var session: Window? { windows.first { $0.windowHours == 5 || $0.label.lowercased().contains("hour") } }
    var weekly: Window? { windows.first { $0.windowHours == 168 || $0.label.lowercased().contains("week") } }
    var weeklyProjection: Projection? { projections.first { $0.label.lowercased().contains("week") } }
}

struct UsageSnapshot: Codable {
    let claude: ClaudeUsage?
    let chatgpt: ChatGPTUsage?
    let fetchedAt: Date
}

enum UsageAPI {
    static func fetch() async throws -> UsageSnapshot {
        guard let key = APIKeyStore.read(), !key.isEmpty,
              let base = SharedSettings.allowedURL(SharedSettings.baseURL) else {
            throw UsageError.invalidConfiguration
        }
        async let claude: ClaudeUsage? = request("api/claude-usage", base: base, key: key)
        async let chatgpt: ChatGPTUsage? = request("api/chatgpt-usage", base: base, key: key)
        let snapshot = UsageSnapshot(claude: await claude, chatgpt: await chatgpt, fetchedAt: Date())
        guard snapshot.claude != nil || snapshot.chatgpt != nil else { throw UsageError.badResponse }
        if let data = try? JSONEncoder().encode(snapshot) {
            SharedSettings.defaults?.set(data, forKey: "lastSnapshot")
        }
        return snapshot
    }

    static func cached() -> UsageSnapshot? {
        guard let data = SharedSettings.defaults?.data(forKey: "lastSnapshot") else { return nil }
        return try? JSONDecoder().decode(UsageSnapshot.self, from: data)
    }

    private static func request<T: Decodable>(_ path: String, base: URL, key: String) async -> T? {
        let url = base.appendingPathComponent(path)
        var request = URLRequest(url: url)
        request.setValue(key, forHTTPHeaderField: "X-API-Key")
        request.timeoutInterval = 20
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { return nil }
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            return nil
        }
    }
}

enum UsageFormat {
    static func date(_ value: String?) -> Date? {
        guard let value else { return nil }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: value) ?? ISO8601DateFormatter().date(from: value)
    }

    static func reset(_ value: String?) -> String {
        guard let date = date(value) else { return "—" }
        return date.formatted(.dateTime.day().month(.abbreviated).hour().minute().locale(Locale(identifier: "id_ID")))
    }

    static func sessionReset(_ value: String?) -> String {
        guard let date = date(value), date > Date() else { return "Not started yet" }
        return reset(value)
    }
}
