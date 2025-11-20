import Cocoa

/// Application delegate for ManagedNebula
class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Decide activation policy after we inspect configuration (handled in MenuBarController)
        
        // Ensure log directory and file exist
        ensureLogDirectoryExists()
        
        // Initialize menu bar controller
        menuBarController = MenuBarController()
        
        print("[AppDelegate] ManagedNebula started")
    }
    
    private func ensureLogDirectoryExists() {
        let logFile = FileManager.NebulaFiles.logFile
        let logDir = logFile.deletingLastPathComponent()
        
        do {
            // Create log directory if needed
            try FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)
            
            // Create empty log file if it doesn't exist
            if !FileManager.default.fileExists(atPath: logFile.path) {
                FileManager.default.createFile(atPath: logFile.path, contents: Data(), attributes: nil)
                print("[AppDelegate] Created log file at: \(logFile.path)")
            }
        } catch {
            print("[AppDelegate] Failed to create log directory: \(error)")
        }
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        print("[AppDelegate] ManagedNebula terminating")
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        // Keep app running even when all windows are closed
        return false
    }
}
