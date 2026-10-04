# AI Usage for macOS (native WidgetKit)

This optional macOS 14+ app and WidgetKit extension display Claude Pro and ChatGPT Plus usage from this repository's local API. The large widget shows 5-hour usage/reset, weekly usage/reset/projection, and safe/unsafe status. Clicking it opens the Mac app rather than iPhone Mirroring.

The widget fetches `/api/claude-usage` and `/api/chatgpt-usage` roughly every 15 minutes, subject to WidgetKit scheduling. Click the circular-arrow button in the header to fetch immediately without opening the app. When the API is unavailable, it displays the last successful snapshot. Claude reset and projection fields require a configured collector; the baseline Claude Desktop cache supplies percentages only.

## Build

1. Install full Xcode from Apple and XcodeGen (`brew install xcodegen`). Open Xcode once to complete setup.
2. Choose a unique reverse-DNS identifier you control (for example, `com.yourname.aiusage`). Replace **every** `com.example` occurrence under this directory with your identifier prefix. This includes `project.yml`, both Info.plist files, both entitlements, and `Shared/UsageData.swift`. The two targets must share the same App Group and Keychain access group.
3. From this directory, run `xcodegen generate` and open `AIUsageMac.xcodeproj` in Xcode. Select your own Apple Development team for both targets. Enable/register the App Group shown in the entitlements. If your signing team cannot provision App Groups or shared Keychain access, the widget cannot read the app's saved key; resolve signing before continuing.
4. Build and run the `AIUsageMac` scheme. Enter the local API URL (normally `http://127.0.0.1:8787`) and the value of `AI_USAGE_API_KEY` from your private `.env`, then click **Simpan dan uji koneksi**.
5. Add **AI Usage** from the macOS widget gallery. The widget is available in the Large size.

Do not commit generated Xcode projects with personal Team IDs, a filled-in `.env`, API keys, provisioning profiles, or usage cache data. This repository includes only source and an example signing namespace. API keys are stored locally in a shared Keychain access group. The App Group holds only the API base URL and usage snapshot. Local HTTP is accepted for localhost only; use HTTPS for a non-local endpoint. Do not expose the API directly to the public internet.
