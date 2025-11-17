import Cocoa

/// Application delegate for ManagedNebula
class AppDelegate: NSObject, NSApplicationDelegate {
    private var menuBarController: MenuBarController?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide dock icon and main menu (menu bar app only)
        NSApp.setActivationPolicy(.accessory)
        
        // Initialize menu bar controller
        menuBarController = MenuBarController()
        
        print("[AppDelegate] ManagedNebula started")
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        print("[AppDelegate] ManagedNebula terminating")
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        // Keep app running even when all windows are closed
        return false
    }
}
