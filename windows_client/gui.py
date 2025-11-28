"""
Managed Nebula Windows GUI Application
System tray application with configuration interface
"""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, Callable
import webbrowser

# For system tray functionality
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# Import our modules
from config import (
    load_config, save_config, get_client_token, set_client_token,
    NEBULA_DIR, CONFIG_FILE
)
from agent import (
    __version__, get_nebula_version, is_nebula_running,
    start_nebula, stop_nebula, get_status, run_once, AGENT_LOG
)

# Service management utilities
try:
    import subprocess
    import ctypes
    ADMIN_AVAILABLE = True
except ImportError:
    ADMIN_AVAILABLE = False


class ConfigWindow:
    """Configuration window for Managed Nebula"""
    
    def __init__(self, on_save: Optional[Callable] = None, on_close: Optional[Callable] = None):
        self.on_save = on_save
        self.on_close = on_close
        self.window = None
        
    def show(self):
        """Show the configuration window"""
        if self.window is not None:
            try:
                self.window.lift()
                self.window.focus_force()
                return
            except tk.TclError:
                pass
        
        self.window = tk.Tk()
        self.window.title("Managed Nebula - Configuration")
        self.window.geometry("500x450")
        self.window.resizable(False, False)
        
        # Try to set icon
        try:
            icon_path = Path(__file__).parent / "installer" / "nebula.ico"
            if icon_path.exists():
                self.window.iconbitmap(str(icon_path))
        except Exception:
            pass
        
        # Load current config
        config = load_config()
        token = get_client_token() or ""
        
        # Create main frame with padding
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Managed Nebula Configuration", font=("Segoe UI", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Server URL
        ttk.Label(main_frame, text="Server URL:").grid(row=1, column=0, sticky="w", pady=5)
        self.server_url_var = tk.StringVar(value=config.get("server_url", ""))
        server_url_entry = ttk.Entry(main_frame, textvariable=self.server_url_var, width=50)
        server_url_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Client Token
        ttk.Label(main_frame, text="Client Token:").grid(row=2, column=0, sticky="w", pady=5)
        self.token_var = tk.StringVar(value=token)
        token_entry = ttk.Entry(main_frame, textvariable=self.token_var, width=50, show="*")
        token_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))
        
        # Show/Hide token button
        self.show_token = tk.BooleanVar(value=False)
        def toggle_token():
            if self.show_token.get():
                token_entry.config(show="")
            else:
                token_entry.config(show="*")
        show_btn = ttk.Checkbutton(main_frame, text="Show", variable=self.show_token, command=toggle_token)
        show_btn.grid(row=2, column=2, padx=5)
        
        # Poll Interval
        ttk.Label(main_frame, text="Poll Interval (hours):").grid(row=3, column=0, sticky="w", pady=5)
        self.poll_interval_var = tk.StringVar(value=str(config.get("poll_interval_hours", 24)))
        poll_entry = ttk.Spinbox(main_frame, from_=1, to=168, textvariable=self.poll_interval_var, width=10)
        poll_entry.grid(row=3, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Log Level
        ttk.Label(main_frame, text="Log Level:").grid(row=4, column=0, sticky="w", pady=5)
        self.log_level_var = tk.StringVar(value=config.get("log_level", "INFO"))
        log_combo = ttk.Combobox(main_frame, textvariable=self.log_level_var, 
                                  values=["DEBUG", "INFO", "WARNING", "ERROR"], state="readonly", width=15)
        log_combo.grid(row=4, column=1, sticky="w", pady=5, padx=(10, 0))
        
        # Auto-start Nebula
        self.auto_start_var = tk.BooleanVar(value=config.get("auto_start_nebula", True))
        auto_start_cb = ttk.Checkbutton(main_frame, text="Auto-start Nebula when service runs", 
                                         variable=self.auto_start_var)
        auto_start_cb.grid(row=5, column=0, columnspan=2, sticky="w", pady=10)
        
        # Separator
        ttk.Separator(main_frame, orient="horizontal").grid(row=6, column=0, columnspan=3, sticky="ew", pady=15)
        
        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=5)
        status_frame.columnconfigure(1, weight=1)
        
        # Nebula status
        nebula_running = is_nebula_running()
        status_text = "Connected" if nebula_running else "Disconnected"
        status_color = "green" if nebula_running else "red"
        
        ttk.Label(status_frame, text="Nebula Status:").grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(status_frame, text=status_text, foreground=status_color)
        self.status_label.grid(row=0, column=1, sticky="w", padx=(10, 0))
        
        # Version info
        ttk.Label(status_frame, text="Agent Version:").grid(row=1, column=0, sticky="w")
        ttk.Label(status_frame, text=__version__).grid(row=1, column=1, sticky="w", padx=(10, 0))
        
        ttk.Label(status_frame, text="Nebula Version:").grid(row=2, column=0, sticky="w")
        ttk.Label(status_frame, text=get_nebula_version()).grid(row=2, column=1, sticky="w", padx=(10, 0))
        
        # Service status
        service_status = get_service_status()
        service_text = {
            "running": "Service Running",
            "stopped": "Service Stopped",
            "installed": "Service Installed",
            "not_installed": "Service Not Installed",
            "unknown": "Unknown"
        }.get(service_status, "Unknown")
        service_color = "green" if service_status == "running" else "orange" if service_status in ["stopped", "installed"] else "red"
        
        ttk.Label(status_frame, text="Windows Service:").grid(row=3, column=0, sticky="w")
        self.service_label = ttk.Label(status_frame, text=service_text, foreground=service_color)
        self.service_label.grid(row=3, column=1, sticky="w", padx=(10, 0))
        
        # Service management button
        if service_status == "not_installed":
            service_btn = ttk.Button(status_frame, text="Install Service", command=self._install_service, width=15)
            service_btn.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        elif service_status == "stopped":
            service_btn = ttk.Button(status_frame, text="Start Service", command=self._start_service, width=15)
            service_btn.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=8, column=0, columnspan=3, pady=20)
        
        # Action buttons
        ttk.Button(btn_frame, text="Save", command=self._save, width=12).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Test Connection", command=self._test_connection, width=15).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="View Logs", command=self._view_logs, width=12).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._close, width=12).pack(side="left", padx=5)
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        
        # Center window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        self.window.mainloop()
    
    def _save(self):
        """Save configuration"""
        # Validate
        server_url = self.server_url_var.get().strip()
        if not server_url:
            messagebox.showerror("Validation Error", "Server URL is required")
            return
        
        try:
            poll_interval = int(self.poll_interval_var.get())
            if poll_interval < 1:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Validation Error", "Poll interval must be a positive number")
            return
        
        # Save config
        config = {
            "server_url": server_url,
            "poll_interval_hours": poll_interval,
            "log_level": self.log_level_var.get(),
            "auto_start_nebula": self.auto_start_var.get(),
        }
        
        save_config(config)
        
        # Save token separately (more secure)
        token = self.token_var.get().strip()
        if token:
            set_client_token(token)
        
        messagebox.showinfo("Success", "Configuration saved successfully!")
        
        if self.on_save:
            self.on_save(config)
        
        self._close()
    
    def _test_connection(self):
        """Test connection to server"""
        server_url = self.server_url_var.get().strip()
        token = self.token_var.get().strip()
        
        if not server_url:
            messagebox.showerror("Error", "Server URL is required")
            return
        
        if not token:
            messagebox.showerror("Error", "Client Token is required")
            return
        
        # Temporarily save and try to fetch config
        try:
            # Set environment for test
            os.environ["SERVER_URL"] = server_url
            os.environ["CLIENT_TOKEN"] = token
            
            success = run_once(restart_on_change=False)
            
            if success:
                messagebox.showinfo("Success", "Connection test successful!\nConfiguration retrieved from server.")
                self._update_status()
            else:
                messagebox.showerror("Error", "Connection test failed.\nCheck the logs for details.")
        except Exception as e:
            messagebox.showerror("Error", f"Connection test failed:\n{str(e)}")
        finally:
            # Clean up environment
            if "SERVER_URL" in os.environ:
                del os.environ["SERVER_URL"]
            if "CLIENT_TOKEN" in os.environ:
                del os.environ["CLIENT_TOKEN"]
    
    def _view_logs(self):
        """Open log file"""
        if AGENT_LOG.exists():
            os.startfile(str(AGENT_LOG))
        else:
            # Open log directory
            AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
            os.startfile(str(AGENT_LOG.parent))
    
    def _update_status(self):
        """Update status display"""
        nebula_running = is_nebula_running()
        status_text = "Connected" if nebula_running else "Disconnected"
        status_color = "green" if nebula_running else "red"
        self.status_label.config(text=status_text, foreground=status_color)
    
    def _refresh_status(self):
        """Refresh status displays including service status"""
        # Update Nebula status
        self._update_status()
        
        # Update service status if label exists
        if hasattr(self, 'service_label'):
            service_status = get_service_status()
            service_text = {
                "running": "Service Running",
                "stopped": "Service Stopped",
                "installed": "Service Installed",
                "not_installed": "Service Not Installed",
                "unknown": "Unknown"
            }.get(service_status, "Unknown")
            service_color = "green" if service_status == "running" else "orange" if service_status in ["stopped", "installed"] else "red"
            self.service_label.config(text=service_text, foreground=service_color)
    
    def _install_service(self):
        """Install the Windows Service"""
        if not is_admin():
            messagebox.showerror(
                "Administrator Required",
                "Installing the service requires administrator privileges.\n\n"
                "Please run this application as Administrator."
            )
            return
        
        # Show progress dialog
        progress_window = tk.Toplevel(self.window)
        progress_window.title("Installing Service")
        progress_window.geometry("400x200")
        progress_window.transient(self.window)
        progress_window.grab_set()
        
        # Center it
        progress_window.update_idletasks()
        x = self.window.winfo_x() + (self.window.winfo_width() - progress_window.winfo_width()) // 2
        y = self.window.winfo_y() + (self.window.winfo_height() - progress_window.winfo_height()) // 2
        progress_window.geometry(f"+{x}+{y}")
        
        progress_label = ttk.Label(progress_window, text="Installing Windows Service...")
        progress_label.pack(pady=20)
        
        progress_text = tk.Text(progress_window, height=8, width=50)
        progress_text.pack(pady=10, padx=10)
        
        def log_progress(msg):
            progress_text.insert(tk.END, msg + "\n")
            progress_text.see(tk.END)
            progress_window.update()
        
        def install_thread():
            try:
                # Find service executable
                service_exe = None
                search_paths = [
                    Path(sys.executable).parent / "NebulaAgentService.exe",
                    Path(__file__).parent / "NebulaAgentService.exe",
                    Path("C:/Program Files/ManagedNebula/NebulaAgentService.exe"),
                    Path(NEBULA_DIR) / "bin" / "NebulaAgentService.exe",
                ]
                
                log_progress("Searching for NebulaAgentService.exe...")
                for path in search_paths:
                    if path.exists():
                        service_exe = path
                        log_progress(f"Found: {path}")
                        break
                
                if not service_exe:
                    log_progress("ERROR: NebulaAgentService.exe not found!")
                    log_progress("")
                    log_progress("Please run build-installer.bat to build the service executable.")
                    messagebox.showerror(
                        "Service Executable Not Found",
                        "NebulaAgentService.exe not found!\n\n"
                        "Please build the service executable first by running:\n"
                        "  build-installer.bat\n\n"
                        "Or ensure it's in one of these locations:\n" +
                        "\n".join(str(p) for p in search_paths)
                    )
                    progress_window.destroy()
                    return
                
                log_progress("")
                log_progress("Creating Windows Service...")
                
                # Create service with sc
                result = subprocess.run(
                    [
                        "sc", "create", "NebulaAgent",
                        f"binPath= {service_exe}",
                        "start= auto",
                        "type= share",
                        "DisplayName= Managed Nebula Agent"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    log_progress("✓ Service created successfully")
                    log_progress("")
                    log_progress("Starting service...")
                    
                    # Start service
                    result = subprocess.run(
                        ["sc", "start", "NebulaAgent"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        log_progress("✓ Service started successfully")
                        log_progress("")
                        log_progress("Service installation complete!")
                        messagebox.showinfo(
                            "Success",
                            "Windows Service installed and started successfully!\n\n"
                            "The service will now start automatically on system boot."
                        )
                    else:
                        log_progress(f"⚠ Warning: Service created but failed to start")
                        log_progress(result.stderr if result.stderr else result.stdout)
                        messagebox.showwarning(
                            "Partial Success",
                            "Service was created but failed to start.\n\n"
                            "Check the Event Viewer for details.\n"
                            "You may need to configure the service first."
                        )
                else:
                    log_progress(f"✗ Failed to create service")
                    log_progress(result.stderr if result.stderr else result.stdout)
                    messagebox.showerror(
                        "Installation Failed",
                        f"Failed to create service:\n\n{result.stderr if result.stderr else result.stdout}"
                    )
                
                progress_window.destroy()
                # Refresh status without recreating window
                if self.window:
                    self._refresh_status()
                
            except Exception as e:
                log_progress(f"\nERROR: {str(e)}")
                messagebox.showerror("Error", f"Service installation failed:\n\n{str(e)}")
                progress_window.destroy()
        
        # Run installation in thread
        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()
    
    def _start_service(self):
        """Start the Windows Service"""
        if not is_admin():
            messagebox.showerror(
                "Administrator Required",
                "Starting the service requires administrator privileges.\n\n"
                "Please run this application as Administrator."
            )
            return
        
        try:
            result = subprocess.run(
                ["sc", "start", "NebulaAgent"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                messagebox.showinfo("Success", "Service started successfully!")
                # Refresh status without recreating window
                if self.window:
                    self._refresh_status()
            else:
                messagebox.showerror(
                    "Error",
                    f"Failed to start service:\n\n{result.stderr if result.stderr else result.stdout}"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start service:\n\n{str(e)}")
    
    def _close(self):
        """Close the window"""
        if self.window:
            self.window.destroy()
            self.window = None
        if self.on_close:
            self.on_close()


class SystemTrayApp:
    """System tray application for Managed Nebula"""
    
    def __init__(self):
        self.icon = None
        self.config_window = None
        self._stop_event = threading.Event()
        
    def create_icon_image(self, color="gray"):
        """Create a simple icon image"""
        # Create a simple colored circle icon
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Choose color based on status
        if color == "green":
            fill_color = (76, 175, 80, 255)  # Green - connected
        elif color == "red":
            fill_color = (244, 67, 54, 255)  # Red - error
        else:
            fill_color = (158, 158, 158, 255)  # Gray - disconnected
        
        # Draw circle
        padding = 4
        draw.ellipse([padding, padding, size-padding, size-padding], fill=fill_color)
        
        # Draw 'N' letter for Nebula
        draw.text((size//2 - 8, size//2 - 12), "N", fill=(255, 255, 255, 255))
        
        return image
    
    def load_icon_image(self):
        """Load icon from file or create default"""
        try:
            icon_path = Path(__file__).parent / "installer" / "nebula.ico"
            if icon_path.exists():
                return Image.open(str(icon_path))
        except Exception:
            pass
        
        # Create default icon
        return self.create_icon_image()
    
    def get_status_icon(self):
        """Get icon based on current status"""
        if is_nebula_running():
            return self.create_icon_image("green")
        return self.create_icon_image("gray")
    
    def create_menu(self):
        """Create system tray menu"""
        # Get current status
        nebula_running = is_nebula_running()
        status_text = "Connected" if nebula_running else "Disconnected"
        connect_text = "Disconnect" if nebula_running else "Connect"
        
        menu_items = [
            pystray.MenuItem(f"Status: {status_text}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(connect_text, self.toggle_connection),
            pystray.MenuItem("Check for Updates", self.check_updates),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Configuration...", self.show_config),
            pystray.MenuItem("View Logs", self.view_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"Agent v{__version__}", None, enabled=False),
            pystray.MenuItem(f"Nebula v{get_nebula_version()}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_app),
        ]
        
        return pystray.Menu(*menu_items)
    
    def toggle_connection(self, icon=None, item=None):
        """Toggle Nebula connection"""
        if is_nebula_running():
            stop_nebula()
        else:
            start_nebula()
        
        # Update icon and menu
        self.update_icon()
    
    def check_updates(self, icon=None, item=None):
        """Check for configuration updates"""
        try:
            success = run_once(restart_on_change=True)
            if success:
                self.update_icon()
        except Exception as e:
            print(f"Update check failed: {e}")
    
    def show_config(self, icon=None, item=None):
        """Show configuration window"""
        def on_save(config):
            self.update_icon()
        
        # Run in main thread
        self.config_window = ConfigWindow(on_save=on_save)
        # Use threading to show window without blocking tray
        thread = threading.Thread(target=self.config_window.show, daemon=True)
        thread.start()
    
    def view_logs(self, icon=None, item=None):
        """Open log file"""
        if AGENT_LOG.exists():
            os.startfile(str(AGENT_LOG))
        else:
            AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
            os.startfile(str(AGENT_LOG.parent))
    
    def update_icon(self):
        """Update tray icon and menu"""
        if self.icon:
            self.icon.icon = self.get_status_icon()
            self.icon.menu = self.create_menu()
    
    def quit_app(self, icon=None, item=None):
        """Quit the application"""
        self._stop_event.set()
        if self.icon:
            self.icon.stop()
    
    def run(self):
        """Run the system tray application"""
        if not TRAY_AVAILABLE:
            print("System tray not available. Install pystray and Pillow:")
            print("  pip install pystray Pillow")
            # Fall back to just showing config window
            window = ConfigWindow()
            window.show()
            return
        
        # Create tray icon
        self.icon = pystray.Icon(
            "ManagedNebula",
            self.get_status_icon(),
            "Managed Nebula",
            self.create_menu()
        )
        
        # Run icon
        self.icon.run()


def main():
    """Main entry point for GUI application"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Managed Nebula Windows GUI")
    parser.add_argument("--config", action="store_true", help="Show configuration window only")
    parser.add_argument("--tray", action="store_true", help="Run as system tray application")
    args = parser.parse_args()
    
    if args.config:
        # Just show config window
        window = ConfigWindow()
        window.show()
    else:
        # Run as tray app (default)
        app = SystemTrayApp()
        app.run()


if __name__ == "__main__":
    main()
