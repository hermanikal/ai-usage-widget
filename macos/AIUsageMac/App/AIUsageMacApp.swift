import SwiftUI
import WidgetKit

@main
struct AIUsageMacApp: App {
    init() {
        // A one-shot, signed CLI import keeps the key out of project files,
        // command arguments, and UI automation logs during local setup.
        if let key = ProcessInfo.processInfo.environment["AI_USAGE_IMPORT_API_KEY"] {
            do {
                try APIKeyStore.save(key)
                WidgetCenter.shared.reloadAllTimelines()
                exit(EXIT_SUCCESS)
            } catch {
                exit(EXIT_FAILURE)
            }
        }
    }

    var body: some Scene {
        WindowGroup("AI Usage") {
            SettingsView()
                .frame(minWidth: 480, minHeight: 310)
        }
        .windowResizability(.contentSize)
    }
}

struct SettingsView: View {
    @State private var baseURL = SharedSettings.baseURL
    @State private var apiKey = ""
    @State private var message = ""
    @State private var isTesting = false

    var body: some View {
        Form {
            Text("AI Usage")
                .font(.title2.bold())
            Text("Widget macOS native untuk Claude Pro dan ChatGPT Plus. Tidak memakai iPhone Mirroring.")
                .foregroundStyle(.secondary)

            TextField("API lokal", text: $baseURL)
                .textFieldStyle(.roundedBorder)
            SecureField("API key", text: $apiKey)
                .textFieldStyle(.roundedBorder)

            HStack {
                Button("Simpan dan uji koneksi") { saveAndTest() }
                    .disabled(isTesting || apiKey.isEmpty)
                if isTesting { ProgressView().controlSize(.small) }
            }
            Text(message).foregroundStyle(.secondary)
            Text("API key disimpan di Keychain bersama yang hanya dapat dibaca aplikasi dan widget ini. URL dan cache angka pemakaian tersimpan di App Group.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(24)
        .onAppear {
            apiKey = APIKeyStore.read() ?? ""
        }
    }

    private func saveAndTest() {
        guard let url = SharedSettings.allowedURL(baseURL) else {
            message = "Gunakan HTTP localhost atau HTTPS untuk host lain."
            return
        }
        guard SharedSettings.defaults != nil else {
            message = "App Group belum tersedia. Periksa Signing & Capabilities di Xcode."
            return
        }
        do {
            try APIKeyStore.save(apiKey)
            SharedSettings.defaults?.set(url.absoluteString.trimmingCharacters(in: CharacterSet(charactersIn: "/")), forKey: "baseURL")
        } catch {
            message = error.localizedDescription
            return
        }
        isTesting = true
        message = "Menguji API…"
        Task {
            do {
                let snapshot = try await UsageAPI.fetch()
                message = "Tersambung: Claude \(snapshot.claude == nil ? "—" : "✓"), ChatGPT \(snapshot.chatgpt == nil ? "—" : "✓"). Tambahkan widget AI Usage dari galeri macOS."
                WidgetCenter.shared.reloadAllTimelines()
            } catch {
                message = error.localizedDescription
            }
            isTesting = false
        }
    }
}
