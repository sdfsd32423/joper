import Foundation
import Postbox

// exteraGram / AyuGram badges: the public list of their developers, official
// channels, supporters and custom badges, the same list their own clients load.
// It is cached on disk and refreshed at most once an hour.
public final class AyuBadges: @unchecked Sendable {
    public enum Badge: Equatable {
        case developer
        case supporter
        case custom(fileId: Int64)
    }

    private struct Lists {
        var developers = Set<Int64>()
        var officialChannels = Set<Int64>()
        var supporters = Set<Int64>()
        var supporterChannels = Set<Int64>()
        var customBadges: [Int64: Int64] = [:]
    }

    public static let shared = AyuBadges()

    private static let urls: [URL] = [
        URL(string: "https://update.ayugram.one/rc/current/desktop2")!,
        URL(string: "https://api.exteragram.app/api/v1/profiles/compact")!
    ]
    private static let refreshInterval: TimeInterval = 60.0 * 60.0

    private let lock = NSLock()
    private var lists: Lists?
    private var lastFetchTimestamp: TimeInterval = 0.0
    private var isFetching = false

    private var cacheUrl: URL? {
        return FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?.appendingPathComponent("ayu_badges.json")
    }

    private init() {
        if let cacheUrl = self.cacheUrl, let data = try? Data(contentsOf: cacheUrl) {
            self.lists = AyuBadges.parse(data)
        }
    }

    public func badge(for peerId: PeerId) -> Badge? {
        self.refreshIfNeeded()

        let id = peerId.id._internalGetInt64Value()
        self.lock.lock()
        defer {
            self.lock.unlock()
        }
        guard let lists = self.lists else {
            return nil
        }
        if peerId.namespace == Namespaces.Peer.CloudUser {
            if let fileId = lists.customBadges[id] {
                return .custom(fileId: fileId)
            } else if lists.developers.contains(id) {
                return .developer
            } else if lists.supporters.contains(id) {
                return .supporter
            }
        } else if peerId.namespace == Namespaces.Peer.CloudChannel {
            if let fileId = lists.customBadges[id] {
                return .custom(fileId: fileId)
            } else if lists.officialChannels.contains(id) {
                return .developer
            } else if lists.supporterChannels.contains(id) {
                return .supporter
            }
        }
        return nil
    }

    private func refreshIfNeeded() {
        let now = Date().timeIntervalSince1970
        self.lock.lock()
        let shouldFetch = !self.isFetching && now - self.lastFetchTimestamp > AyuBadges.refreshInterval
        if shouldFetch {
            self.isFetching = true
            self.lastFetchTimestamp = now
        }
        self.lock.unlock()

        if shouldFetch {
            self.fetch(urlIndex: 0)
        }
    }

    private func fetch(urlIndex: Int) {
        if urlIndex >= AyuBadges.urls.count {
            self.lock.lock()
            self.isFetching = false
            // Retry sooner than the regular interval after a failure.
            self.lastFetchTimestamp = Date().timeIntervalSince1970 - AyuBadges.refreshInterval + 5.0 * 60.0
            self.lock.unlock()
            return
        }
        var request = URLRequest(url: AyuBadges.urls[urlIndex])
        request.timeoutInterval = 15.0
        URLSession.shared.dataTask(with: request, completionHandler: { [weak self] data, response, _ in
            guard let self else {
                return
            }
            let statusCode = (response as? HTTPURLResponse)?.statusCode ?? 0
            guard statusCode == 200, let data, let lists = AyuBadges.parse(data) else {
                self.fetch(urlIndex: urlIndex + 1)
                return
            }
            if let cacheUrl = self.cacheUrl {
                try? data.write(to: cacheUrl, options: .atomic)
            }
            self.lock.lock()
            self.lists = lists
            self.isFetching = false
            self.lock.unlock()
        }).resume()
    }

    private static func int64(_ value: Any?) -> Int64? {
        if let number = value as? NSNumber {
            return number.int64Value
        } else if let string = value as? String {
            return Int64(string)
        }
        return nil
    }

    private static func idSet(_ value: Any?) -> Set<Int64> {
        guard let array = value as? [Any] else {
            return Set()
        }
        var result = Set<Int64>()
        for item in array {
            if let id = AyuBadges.int64(item), id != 0 {
                result.insert(id)
            }
        }
        return result
    }

    private static func parse(_ data: Data) -> Lists? {
        guard let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else {
            return nil
        }
        var lists = Lists()
        lists.developers = AyuBadges.idSet(root["developers"])
        lists.officialChannels = AyuBadges.idSet(root["officialChannels"])
        lists.supporters = AyuBadges.idSet(root["supporters"])
        lists.supporterChannels = AyuBadges.idSet(root["supporterChannels"])
        if let customBadges = root["customBadges"] as? [Any] {
            for item in customBadges {
                guard let object = item as? [String: Any], let id = AyuBadges.int64(object["id"]), id != 0 else {
                    continue
                }
                guard let badge = object["badge"] as? [String: Any], let fileId = AyuBadges.int64(badge["documentId"]), fileId != 0 else {
                    continue
                }
                lists.customBadges[id] = fileId
            }
        }
        return lists
    }
}
