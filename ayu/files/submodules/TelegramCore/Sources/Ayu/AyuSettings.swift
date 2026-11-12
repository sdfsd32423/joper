import Foundation

// Client-side settings of the mod. Stored in the app's UserDefaults: they are
// local to this device and never synced to Telegram servers.
public enum AyuSettings {
    private static let ghostModeKey = "ayu.ghostMode"

    // Ghost mode: do not send read receipts, online status, typing status
    // and story views to the server.
    public static var ghostMode: Bool {
        get {
            return UserDefaults.standard.bool(forKey: AyuSettings.ghostModeKey)
        }
        set {
            UserDefaults.standard.set(newValue, forKey: AyuSettings.ghostModeKey)
        }
    }
}
