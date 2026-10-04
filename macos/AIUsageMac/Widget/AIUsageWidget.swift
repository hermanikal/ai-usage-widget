import AppIntents
import SwiftUI
import WidgetKit

struct RefreshUsageIntent: AppIntent {
    static var title: LocalizedStringResource = "Refresh AI Usage"
    static var description = IntentDescription("Ambil data terbaru Claude Pro dan ChatGPT Plus.")

    func perform() async throws -> some IntentResult {
        // WidgetKit reloads this widget's timeline when the intent returns.
        // Fetch first so the new snapshot is ready in the shared App Group.
        _ = try? await UsageAPI.fetch()
        return .result()
    }
}

struct UsageEntry: TimelineEntry {
    let date: Date
    let snapshot: UsageSnapshot?
}

struct UsageProvider: TimelineProvider {
    func placeholder(in context: Context) -> UsageEntry {
        UsageEntry(date: Date(), snapshot: nil)
    }

    func getSnapshot(in context: Context, completion: @escaping (UsageEntry) -> Void) {
        completion(UsageEntry(date: Date(), snapshot: UsageAPI.cached()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<UsageEntry>) -> Void) {
        Task {
            let snapshot = (try? await UsageAPI.fetch()) ?? UsageAPI.cached()
            let now = Date()
            completion(Timeline(entries: [UsageEntry(date: now, snapshot: snapshot)],
                                policy: .after(now.addingTimeInterval(15 * 60))))
        }
    }
}

struct MeterRow: View {
    let label: String
    let percent: Double?

    var body: some View {
        HStack(spacing: 7) {
            Text(label).frame(width: 55, alignment: .leading)
                .foregroundStyle(.secondary)
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule().fill(.white.opacity(0.14))
                    Capsule()
                        .fill(color)
                        .frame(width: max(0, geometry.size.width * min(max((percent ?? 0) / 100, 0), 1)))
                }
            }
            .frame(height: 7)
            Text(percent.map { "\(Int($0.rounded()))%" } ?? "—")
                .fontWeight(.bold)
                .foregroundStyle(color)
                .frame(width: 42, alignment: .trailing)
        }
        .font(.caption)
    }

    private var color: Color {
        guard let percent else { return .gray }
        if percent < 50 { return .green }
        if percent < 75 { return .yellow }
        if percent < 90 { return .orange }
        return .red
    }
}

struct ProviderSection: View {
    let title: String
    let brand: Color
    let session: Double?
    let sessionReset: String?
    let weekly: Double?
    let weeklyReset: String?
    let projected: Double?
    let safe: Bool?
    let notStarted: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 7) {
                Circle().fill(brand).frame(width: 10, height: 10)
                Text(title).font(.headline)
            }
            MeterRow(label: "5 hour", percent: session)
            Text("5h reset: \(UsageFormat.sessionReset(sessionReset))")
                .font(.caption2).foregroundStyle(.secondary)
            MeterRow(label: "Weekly", percent: weekly)
            HStack(spacing: 3) {
                Text("Reset \(UsageFormat.reset(weeklyReset))")
                if let projected { Text("· ~\(projected.formatted(.number.precision(.fractionLength(0...1))))% weekly") }
            }
            .font(.caption2)
            .foregroundStyle(safe == false ? .orange : .green)
            if notStarted {
                Text("ℹ️ Belum ada aktivitas — proyeksi n/a")
                    .foregroundStyle(.secondary)
            } else if let safe {
                Text(safe ? "✅ Aman sampai reset" : "⚠️ Tidak aman sebelum reset")
                    .foregroundStyle(safe ? .green : .orange)
            }
        }
        .font(.caption)
    }
}

struct UsageWidgetView: View {
    let entry: UsageEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("AI Usage").font(.title3.bold())
                Spacer()
                Button(intent: RefreshUsageIntent()) {
                    Image(systemName: "arrow.clockwise")
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Refresh AI Usage")
            }
            if let snapshot = entry.snapshot {
                let claude = snapshot.claude
                ProviderSection(
                    title: "Claude Pro", brand: Color(red: 0.85, green: 0.47, blue: 0.34),
                    session: claude?.session?.pctActual,
                    sessionReset: claude?.session?.resetsAt,
                    weekly: claude?.weekly?.pctActual,
                    weeklyReset: claude?.weekly?.resetsAt ?? claude?.projection?.resetAt,
                    projected: claude?.projection?.projectedPctAtReset,
                    safe: claude?.projection?.safeUntilReset,
                    notStarted: claude?.projection?.status == "not_started"
                )
                let chatgpt = snapshot.chatgpt
                ProviderSection(
                    title: "ChatGPT Plus", brand: Color(red: 0.06, green: 0.64, blue: 0.50),
                    session: chatgpt?.session?.usedPercent,
                    sessionReset: chatgpt?.session?.resetAt,
                    weekly: chatgpt?.weekly?.usedPercent,
                    weeklyReset: chatgpt?.weekly?.resetAt ?? chatgpt?.weeklyProjection?.resetAt,
                    projected: chatgpt?.weeklyProjection?.projectedPctAtReset,
                    safe: chatgpt?.weeklyProjection?.safeUntilReset,
                    notStarted: chatgpt?.weeklyProjection?.status == "not_started"
                )
                Spacer(minLength: 0)
                Text("↻ \(snapshot.fetchedAt.formatted(.dateTime.hour().minute())) WIB")
                    .font(.caption2).foregroundStyle(.secondary)
            } else {
                Text("Buka aplikasi AI Usage untuk mengatur API lokal.")
                    .font(.caption).foregroundStyle(.secondary)
                Spacer()
            }
        }
        .padding(16)
        .containerBackground(Color(red: 0.10, green: 0.10, blue: 0.10), for: .widget)
        .foregroundStyle(.white)
    }
}

struct AIUsageWidget: Widget {
    let kind = "AIUsageWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: UsageProvider()) { entry in
            UsageWidgetView(entry: entry)
        }
        .configurationDisplayName("AI Usage")
        .description("Claude Pro dan ChatGPT Plus tanpa iPhone Mirroring")
        .supportedFamilies([.systemLarge])
    }
}

@main
struct AIUsageWidgets: WidgetBundle {
    var body: some Widget { AIUsageWidget() }
}
