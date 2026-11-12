import Foundation
import UIKit
import TelegramCore

// Turns an exteraGram / AyuGram badge into content for EmojiStatusComponent.
public enum AyuBadgeContent {
    public static func content(peerId: EnginePeer.Id, accentColor: UIColor, placeholderColor: UIColor) -> EmojiStatusComponent.Content? {
        guard let badge = AyuBadges.shared.badge(for: peerId) else {
            return nil
        }
        switch badge {
        case let .custom(fileId):
            return .animation(content: .customEmoji(fileId: fileId), size: CGSize(width: 32.0, height: 32.0), placeholderColor: placeholderColor, themeColor: accentColor, loopMode: .count(0))
        case .developer:
            return .image(image: AyuBadgeImageCache.shared.image(isDeveloper: true, color: accentColor), tintColor: nil)
        case .supporter:
            return .image(image: AyuBadgeImageCache.shared.image(isDeveloper: false, color: accentColor), tintColor: nil)
        }
    }
}

// Images are drawn once per color: EmojiStatusComponent compares them by identity.
private final class AyuBadgeImageCache: @unchecked Sendable {
    static let shared = AyuBadgeImageCache()

    private let lock = NSLock()
    private var images: [String: UIImage] = [:]

    func image(isDeveloper: Bool, color: UIColor) -> UIImage {
        var red: CGFloat = 0.0
        var green: CGFloat = 0.0
        var blue: CGFloat = 0.0
        var alpha: CGFloat = 0.0
        color.getRed(&red, green: &green, blue: &blue, alpha: &alpha)
        let key = "\(isDeveloper)_\(Int(red * 255.0))_\(Int(green * 255.0))_\(Int(blue * 255.0))_\(Int(alpha * 255.0))"

        self.lock.lock()
        defer {
            self.lock.unlock()
        }
        if let image = self.images[key] {
            return image
        }
        let image = AyuBadgeImageCache.draw(isDeveloper: isDeveloper, color: color)
        self.images[key] = image
        return image
    }

    // A paper plane; developers get it on a filled circle.
    private static func draw(isDeveloper: Bool, color: UIColor) -> UIImage {
        let size = CGSize(width: 20.0, height: 20.0)
        let renderer = UIGraphicsImageRenderer(size: size)
        return renderer.image { _ in
            let plane = UIBezierPath()
            if isDeveloper {
                color.setFill()
                UIBezierPath(ovalIn: CGRect(origin: CGPoint(), size: size)).fill()
                plane.move(to: CGPoint(x: 4.5, y: 9.6))
                plane.addLine(to: CGPoint(x: 15.5, y: 4.8))
                plane.addLine(to: CGPoint(x: 11.6, y: 15.4))
                plane.addLine(to: CGPoint(x: 9.6, y: 10.9))
                plane.close()
                UIColor.white.setFill()
            } else {
                plane.move(to: CGPoint(x: 1.5, y: 9.4))
                plane.addLine(to: CGPoint(x: 18.5, y: 2.0))
                plane.addLine(to: CGPoint(x: 12.4, y: 18.4))
                plane.addLine(to: CGPoint(x: 9.3, y: 11.4))
                plane.close()
                color.setFill()
            }
            plane.fill()
        }
    }
}
