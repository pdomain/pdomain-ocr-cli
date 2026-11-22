import AppKit
import Foundation

final class Setup: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private let window = NSWindow(
        contentRect: NSRect(x: 0, y: 0, width: 600, height: 460),
        styleMask: [.titled, .closable, .miniaturizable, .resizable],
        backing: .buffered, defer: false
    )
    private let status = NSTextField(wrappingLabelWithString: "Checking this Mac…")
    private let models = NSButton(checkboxWithTitle: "Download OCR models during setup", target: nil, action: nil)
    private let updates = NSButton(checkboxWithTitle: "Automatically check for updates", target: nil, action: nil)
    private let mode = NSButton(title: "Uninstall…", target: nil, action: nil)
    private let progress = NSProgressIndicator()
    private let log = NSTextView()
    private let install = NSButton(title: "Install", target: nil, action: nil)
    private let reveal = NSButton(title: "Show in Finder", target: nil, action: nil)
    private let close = NSButton(title: "Cancel", target: nil, action: nil)
    private var running = false
    private var removing = ProcessInfo.processInfo.arguments.contains("--remove")
    private var removalComplete = false
    private var cached = false
    private var installedLauncher: URL?

    private var worker: URL {
        Bundle.main.resourceURL!.appendingPathComponent("payload/setup-worker.sh")
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        window.minSize = NSSize(width: 520, height: 390)
        window.delegate = self
        let title = NSTextField(labelWithString: "OCR CLI Setup")
        title.font = .systemFont(ofSize: 22, weight: .semibold)
        mode.target = self
        mode.action = #selector(switchMode)
        install.target = self
        install.action = #selector(begin)
        install.isEnabled = false
        reveal.target = self
        reveal.action = #selector(showLauncher)
        reveal.isHidden = true
        close.target = self
        close.action = #selector(quit)
        close.keyEquivalent = "\u{1b}"

        progress.style = .bar
        progress.isIndeterminate = true
        progress.minValue = 0
        progress.maxValue = 100
        progress.isHidden = true

        let scroll = NSTextView.scrollableTextView()
        scroll.documentView = log
        scroll.hasVerticalScroller = true
        scroll.borderType = .bezelBorder
        log.isEditable = false
        log.font = .monospacedSystemFont(ofSize: 11, weight: .regular)
        log.isVerticallyResizable = true
        log.autoresizingMask = [.width]
        log.textContainer?.widthTracksTextView = true
        log.textContainerInset = NSSize(width: 8, height: 8)

        let buttons = NSStackView(views: [close, reveal, install])
        buttons.orientation = .horizontal
        buttons.spacing = 10
        let stack = NSStackView(views: [title, mode, status, models, updates, progress, scroll, buttons])
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 10
        stack.translatesAutoresizingMaskIntoConstraints = false
        let content = window.contentView!
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 22),
            stack.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -22),
            stack.topAnchor.constraint(equalTo: content.topAnchor, constant: 18),
            stack.bottomAnchor.constraint(equalTo: content.bottomAnchor, constant: -18),
            status.widthAnchor.constraint(equalTo: stack.widthAnchor),
            progress.widthAnchor.constraint(equalTo: stack.widthAnchor),
            scroll.widthAnchor.constraint(equalTo: stack.widthAnchor),
            scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 130),
            buttons.trailingAnchor.constraint(equalTo: stack.trailingAnchor),
        ])
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        checkMode()
    }

    @objc private func switchMode() {
        removing.toggle()
        checkMode()
    }

    private func checkMode() {
        window.title = removing ? "Uninstall OCR CLI" : "Install OCR CLI"
        mode.title = removing ? "Back to Install" : "Uninstall…"
        install.title = removing ? "Uninstall OCR CLI" : "Install"
        install.keyEquivalent = removing ? "" : "\r"
        close.title = "Cancel"
        close.isHidden = false
        models.isHidden = removing
        models.title = "Download OCR models during setup"
        models.state = .on
        updates.title = removing ? "Also clear OCR CLI update settings" : "Automatically check for updates"
        updates.state = .off
        reveal.isHidden = true
        installedLauncher = nil
        cached = false
        removalComplete = false
        log.string = ""
        status.stringValue = removing ? "Checking what can be removed…" : "Checking this Mac…"
        for button in [mode, models, updates, install] { button.isEnabled = false }
        run([removing ? "remove-preview" : "probe"]) { [weak self] result in
            guard let self else { return }
            self.mode.isEnabled = true
            if self.removing {
                self.status.stringValue = result == 0
                    ? "Review the paths below before uninstalling."
                    : "Setup could not verify the CLI storage. See the details below."
            } else {
                self.status.stringValue = result == 0
                    ? "Review the checks below, then choose what to include."
                    : "Setup could not check this Mac. You can still try installing."
            }
            self.models.isEnabled = !self.removing && !self.cached
            self.updates.isEnabled = !self.removing || result == 0
            self.install.isEnabled = self.updates.isEnabled
        }
    }

    @objc private func begin() {
        if removalComplete {
            quit()
            return
        }
        if let installedLauncher {
            let path = installedLauncher.path.replacingOccurrences(of: "'", with: "'\"'\"'")
            let clipboard = NSPasteboard.general
            clipboard.clearContents()
            if clipboard.setString("'\(path)' --help", forType: .string) {
                status.stringValue = "Command copied. Paste it into Terminal to see the available options."
            }
            return
        }
        running = true
        for button in [mode, models, updates, install, close] { button.isEnabled = false }
        status.stringValue = removing ? "Starting removal…" : "Starting setup…"
        progress.isHidden = false
        progress.isIndeterminate = true
        progress.startAnimation(nil)
        log.string = ""
        let modelChoice = models.state == .on ? "download" : "skip"
        let updateChoice = updates.state == .on ? "enabled" : "disabled"
        let arguments = removing
            ? ["remove", updates.state == .on ? "remove-settings" : "keep-settings"]
            : ["install", modelChoice, updateChoice]
        run(arguments) { [weak self] result in
            guard let self else { return }
            self.running = false
            self.progress.stopAnimation(nil)
            self.progress.isHidden = true
            self.install.isEnabled = true
            self.close.isEnabled = true
            self.mode.isEnabled = true
            if self.removing {
                self.removalComplete = result == 0
                self.status.stringValue = result == 0
                    ? "OCR CLI is absent from the selected uv tool directory."
                    : "Removal did not finish. See the log below, then retry."
                self.install.title = result == 0 ? "Done" : "Retry"
                self.close.isHidden = result == 0
                self.updates.isEnabled = result != 0
            } else if result == 0, let launcher = self.installedLauncher,
               FileManager.default.isExecutableFile(atPath: launcher.path) {
                self.status.stringValue = "OCR CLI is ready. Copy the command and paste it into Terminal to get started."
                self.install.title = "Copy Terminal Command"
                self.close.title = "Close"
                self.reveal.isHidden = false
            } else {
                self.installedLauncher = nil
                self.status.stringValue = "Setup did not finish. See the log below, then retry."
                self.install.title = "Retry"
                self.models.isEnabled = !self.cached
                self.updates.isEnabled = true
            }
        }
    }

    @objc private func showLauncher() {
        if let installedLauncher { NSWorkspace.shared.activateFileViewerSelecting([installedLauncher]) }
    }

    @objc private func quit() {
        if !running { NSApp.terminate(nil) }
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool { !running }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        running ? .terminateCancel : .terminateNow
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    private func receive(_ line: String) {
        if line.hasPrefix("OCR_SETUP_STAGE ") {
            status.stringValue = String(line.dropFirst("OCR_SETUP_STAGE ".count))
            progress.isIndeterminate = true
            progress.startAnimation(nil)
            return
        }
        if line.hasPrefix("OCR_SETUP_LAUNCHER ") {
            installedLauncher = URL(fileURLWithPath: String(line.dropFirst("OCR_SETUP_LAUNCHER ".count)))
            return
        }
        if line == "OCR_SETUP_UPDATES enabled" {
            updates.state = .on
            return
        }
        if line == "OCR_SETUP_MODELS cached" {
            cached = true
            models.state = .off
            models.title = "OCR models already downloaded"
            return
        }
        log.textStorage?.append(NSAttributedString(string: line + "\n", attributes: [
            .font: NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
        ]))
        if let text = log.textStorage {
            log.scrollRangeToVisible(NSRange(location: text.length, length: 0))
        }
    }

    private func run(_ arguments: [String], finished: @escaping (Int32) -> Void) {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/sh")
        task.arguments = [worker.path] + arguments
        let output = Pipe()
        task.standardInput = FileHandle.nullDevice
        task.standardOutput = output
        task.standardError = output
        do {
            try task.run()
        } catch {
            receive(error.localizedDescription)
            finished(1)
            return
        }
        DispatchQueue.global(qos: .userInitiated).async {
            var pending = Data()
            let handle = output.fileHandleForReading
            while true {
                let chunk = handle.availableData
                if chunk.isEmpty { break }
                pending.append(chunk)
                while let newline = pending.firstIndex(of: 10) {
                    let line = String(decoding: pending[..<newline], as: UTF8.self)
                    pending.removeSubrange(...newline)
                    DispatchQueue.main.async { self.receive(line) }
                }
            }
            if !pending.isEmpty {
                let line = String(decoding: pending, as: UTF8.self)
                DispatchQueue.main.async { self.receive(line) }
            }
            task.waitUntilExit()
            DispatchQueue.main.async { finished(task.terminationStatus) }
        }
    }
}

let application = NSApplication.shared
let setup = Setup()
application.setActivationPolicy(.regular)
application.delegate = setup
application.run()
