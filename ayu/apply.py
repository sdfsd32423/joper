#!/usr/bin/env python3
"""Applies the mod on top of a Telegram-iOS checkout.

Usage: python3 ayu/apply.py <path-to-Telegram-iOS> [--check]

1. Copies everything under ayu/files/ into the checkout (new source files).
2. Applies anchored edits to upstream files. Every anchor must occur exactly
   once; if upstream changed and an anchor no longer matches, the script stops
   with an error naming the edit, instead of producing a half-patched tree.

--check only verifies that all anchors match, without writing anything.
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(HERE, "files")

PRIVACY = "submodules/SettingsUI/Sources/Privacy and Security/PrivacyAndSecurityController.swift"
PEER_INFO_HEADER = "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoHeaderNode.swift"
CHAT_LIST_ITEM = "submodules/ChatListUI/Sources/Node/ChatListItem.swift"

# (name, path, anchor, mode, text): mode is "before", "after" or "replace".
EDITS = [
    # --- Ghost mode: online status -------------------------------------------
    (
        "presence: stay offline",
        "submodules/TelegramCore/Sources/State/ManagedAccountPresence.swift",
        "        let request: Signal<Api.Bool, MTRpcError>\n        if isOnline {\n",
        "replace",
        "        let request: Signal<Api.Bool, MTRpcError>\n        if isOnline && !AyuSettings.ghostMode {\n",
    ),
    # --- Ghost mode: typing ----------------------------------------------------
    (
        "typing: do not send",
        "submodules/TelegramCore/Sources/State/ManagedLocalInputActivities.swift",
        "        if let peer = transaction.getPeer(peerId) {\n"
        "            if peerId == accountPeerId {\n"
        "                return .complete()\n"
        "            }\n",
        "after",
        "            if AyuSettings.ghostMode {\n"
        "                var isGroupCallSpeaking = false\n"
        "                if let activity = activity, case .speakingInGroupCall = activity {\n"
        "                    isGroupCallSpeaking = true\n"
        "                }\n"
        "                if !isGroupCallSpeaking {\n"
        "                    return .complete()\n"
        "                }\n"
        "            }\n",
    ),
    # --- Ghost mode: read receipts --------------------------------------------
    (
        "read receipts: do not push",
        "submodules/TelegramCore/Sources/State/SynchronizePeerReadState.swift",
        "private func pushPeerReadState(network: Network, postbox: Postbox, stateManager: AccountStateManager, "
        "peerId: PeerId, readState: PeerReadState) -> Signal<PeerReadState, PeerReadStateValidationError> {\n",
        "after",
        "    if AyuSettings.ghostMode {\n"
        "        return .single(readState)\n"
        "    }\n",
    ),
    # --- Ghost mode: stories ---------------------------------------------------
    (
        "stories: do not mark seen",
        "submodules/TelegramCore/Sources/State/ManagedSynchronizeViewStoriesOperations.swift",
        "    return network.request(Api.functions.stories.readStories(peer: inputPeer, maxId: operation.storyId))\n",
        "before",
        "    if AyuSettings.ghostMode {\n"
        "        return .single(Void())\n"
        "    }\n",
    ),
    (
        "stories: do not count views",
        "submodules/TelegramCore/Sources/TelegramEngine/Messages/Stories.swift",
        "            return account.network.request(Api.functions.stories.incrementStoryViews(peer: inputPeer, id: [id]))\n",
        "before",
        "            if AyuSettings.ghostMode {\n"
        "                return .complete()\n"
        "            }\n",
    ),
    # --- Settings UI: Privacy and Security -> Ghost mode switch ----------------
    (
        "settings: section",
        PRIVACY,
        "    case loginEmail\n    case linkHandling\n}\n",
        "replace",
        "    case loginEmail\n    case linkHandling\n    case ayuGhost\n}\n",
    ),
    (
        "settings: entry cases",
        PRIVACY,
        "    case openLinksIn(PresentationTheme, String, String)\n",
        "after",
        "    case ayuGhostHeader(String)\n"
        "    case ayuGhostMode(String, Bool)\n"
        "    case ayuGhostInfo(String)\n",
    ),
    (
        "settings: entry section",
        PRIVACY,
        "        case .openLinksIn:\n            return PrivacyAndSecuritySection.linkHandling.rawValue\n",
        "before",
        "        case .ayuGhostHeader, .ayuGhostMode, .ayuGhostInfo:\n"
        "            return PrivacyAndSecuritySection.ayuGhost.rawValue\n",
    ),
    (
        "settings: stable ids",
        PRIVACY,
        "            case .openLinksIn:\n                return 33\n",
        "before",
        "            case .ayuGhostHeader:\n"
        "                return -3\n"
        "            case .ayuGhostMode:\n"
        "                return -2\n"
        "            case .ayuGhostInfo:\n"
        "                return -1\n",
    ),
    (
        "settings: equality",
        PRIVACY,
        "            case let .openLinksIn(lhsTheme, lhsText, lhsValue):\n",
        "before",
        "            case let .ayuGhostHeader(text):\n"
        "                if case .ayuGhostHeader(text) = rhs {\n"
        "                    return true\n"
        "                } else {\n"
        "                    return false\n"
        "                }\n"
        "            case let .ayuGhostMode(text, value):\n"
        "                if case .ayuGhostMode(text, value) = rhs {\n"
        "                    return true\n"
        "                } else {\n"
        "                    return false\n"
        "                }\n"
        "            case let .ayuGhostInfo(text):\n"
        "                if case .ayuGhostInfo(text) = rhs {\n"
        "                    return true\n"
        "                } else {\n"
        "                    return false\n"
        "                }\n",
    ),
    (
        "settings: list items",
        PRIVACY,
        "            case let .openLinksIn(_, text, value):\n",
        "before",
        "            case let .ayuGhostHeader(text):\n"
        "                return ItemListSectionHeaderItem(presentationData: presentationData, text: text, sectionId: self.section)\n"
        "            case let .ayuGhostMode(text, value):\n"
        "                return ItemListSwitchItem(presentationData: presentationData, systemStyle: .glass, title: text, value: value, sectionId: self.section, style: .blocks, updated: { value in\n"
        "                    AyuSettings.ghostMode = value\n"
        "                })\n"
        "            case let .ayuGhostInfo(text):\n"
        "                return ItemListTextItem(presentationData: presentationData, text: .plain(text), sectionId: self.section)\n",
    ),
    (
        "settings: entries",
        PRIVACY,
        "    var entries: [PrivacyAndSecurityEntry] = []\n",
        "after",
        "    entries.append(.ayuGhostHeader(\"РЕЖИМ ПРИЗРАКА\"))\n"
        "    entries.append(.ayuGhostMode(\"Режим призрака\", AyuSettings.ghostMode))\n"
        "    entries.append(.ayuGhostInfo(\"Не отправлять «прочитано», «в сети», «печатает» и просмотры историй. "
        "Когда вы отправляете сообщение, сервер всё равно покажет вас в сети.\"))\n",
    ),
    # --- exteraGram / AyuGram badges -------------------------------------------
    (
        "badges: profile header",
        PEER_INFO_HEADER,
        "            default:\n"
        "                emojiRegularStatusContent = .none\n"
        "                emojiExpandedStatusContent = .none\n"
        "            }\n"
        "            \n"
        "            let iconSize = self.titleVerifiedIconView.update(\n",
        "replace",
        "            default:\n"
        "                if let peer, let ayuRegular = AyuBadgeContent.content(peerId: peer.id, accentColor: presentationData.theme.list.itemAccentColor, placeholderColor: presentationData.theme.list.mediaPlaceholderColor), let ayuExpanded = AyuBadgeContent.content(peerId: peer.id, accentColor: navigationContentsAccentColor, placeholderColor: navigationContentsAccentColor) {\n"
        "                    emojiRegularStatusContent = ayuRegular\n"
        "                    emojiExpandedStatusContent = ayuExpanded\n"
        "                } else {\n"
        "                    emojiRegularStatusContent = .none\n"
        "                    emojiExpandedStatusContent = .none\n"
        "                }\n"
        "            }\n"
        "            \n"
        "            let iconSize = self.titleVerifiedIconView.update(\n",
    ),
    (
        "badges: chat list",
        CHAT_LIST_ITEM,
        "            if case let .peer(peerData) = item.content, peerData.isSideListAllThreadsItem {\n"
        "                // \"All Messages\" is not the peer's own title: no status or verification marks.\n",
        "before",
        "            if !isPeerGroup && !isAccountPeer && threadInfo == nil && !displayAsMessage && currentVerifiedIconContent == nil, case let .chat(itemPeer) = contentPeer, let peer = itemPeer.chatOrMonoforumMainPeer, let ayuContent = AyuBadgeContent.content(peerId: peer.id, accentColor: item.presentationData.theme.list.itemAccentColor, placeholderColor: item.presentationData.theme.list.mediaPlaceholderColor) {\n"
        "                currentVerifiedIconContent = ayuContent\n"
        "            }\n",
    ),
]


def fail(message):
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv
    if len(args) != 1:
        fail(__doc__)
    root = args[0]
    if not os.path.isdir(os.path.join(root, "submodules")):
        fail("{} does not look like a Telegram-iOS checkout".format(root))

    contents = {}
    for name, path, anchor, mode, text in EDITS:
        full = os.path.join(root, path)
        if path not in contents:
            if not os.path.isfile(full):
                fail("[{}] file not found: {}".format(name, path))
            with open(full, "r", encoding="utf-8", newline="") as f:
                contents[path] = f.read()
        source = contents[path]
        count = source.count(anchor)
        if count != 1:
            fail("[{}] anchor found {} times in {} (expected 1). Upstream changed; update ayu/apply.py.".format(name, count, path))
        if mode == "before":
            new = text + anchor
        elif mode == "after":
            new = anchor + text
        elif mode == "replace":
            new = text
        else:
            fail("[{}] unknown mode {}".format(name, mode))
        contents[path] = source.replace(anchor, new, 1)
        print("ok   " + name)

    if check_only:
        print("All {} anchors match.".format(len(EDITS)))
        return

    for path, source in contents.items():
        with open(os.path.join(root, path), "w", encoding="utf-8", newline="") as f:
            f.write(source)

    for dirpath, _, filenames in os.walk(FILES_DIR):
        for filename in filenames:
            src = os.path.join(dirpath, filename)
            rel = os.path.relpath(src, FILES_DIR)
            dst = os.path.join(root, rel)
            if os.path.exists(dst):
                fail("refusing to overwrite upstream file {}".format(rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            print("add  " + rel.replace(os.sep, "/"))

    print("Mod applied.")


if __name__ == "__main__":
    main()
