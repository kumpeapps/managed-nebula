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


def is_admin():
    """Check if running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def get_service_status():
    """Check if Nebula Agent service is installed and its status"""
    try:
        result = subprocess.run(
            ["sc", "query", "NebulaAgent"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            output = result.stdout
            if "RUNNING" in output:
                return "running"
            elif "STOPPED" in output:
                return "stopped"
            else:
                return "installed"
        return "not_installed"
    except Exception:
        return "unknown"


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
                self.window = None
        
        # Always create a new Tk root for the config window
        # This ensures it runs independently with its own event loop
        self.window = tk.Tk()
        self.window.title("Managed Nebula - Configuration")
        self.window.geometry("520x540")
        self.window.resizable(False, False)
        
        # Ensure window stays on top initially
        self.window.attributes('-topmost', True)
        self.window.after(100, lambda: self.window.attributes('-topmost', False))
        
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
        
        # Service management buttons
        if service_status == "not_installed":
            ttk.Button(status_frame, text="Install Service", command=self._install_service, width=18).grid(row=4, column=0, columnspan=2, pady=(10, 0))
        elif service_status == "stopped":
            ttk.Button(status_frame, text="Start Service", command=self._start_service, width=18).grid(row=4, column=0, columnspan=2, pady=(10, 0))
            ttk.Button(status_frame, text="Uninstall Service", command=self._uninstall_service, width=18).grid(row=5, column=0, columnspan=2, pady=(6, 0))
        elif service_status == "running" or service_status == "installed":
            ttk.Button(status_frame, text="Uninstall Service", command=self._uninstall_service, width=18).grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(20, 10))
        main_frame.rowconfigure(8, weight=0)
        for i in range(3):
            main_frame.columnconfigure(i, weight=1)
        
        # Action buttons
        ttk.Button(btn_frame, text="Save", command=self._save, width=14).pack(side="left", padx=6, pady=4)
        ttk.Button(btn_frame, text="Test Connection", command=self._test_connection, width=18).pack(side="left", padx=6, pady=4)
        ttk.Button(btn_frame, text="View Logs", command=self._view_logs, width=14).pack(side="left", padx=6, pady=4)
        ttk.Button(btn_frame, text="Cancel", command=self._close, width=14).pack(side="left", padx=6, pady=4)
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        
        # Center window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Only call mainloop if we're running standalone (not from tray)
        # If in a thread, the thread will keep the window alive
        try:
            # Check if we're in the main thread
            if threading.current_thread() is threading.main_thread():
                self.window.mainloop()
            else:
                # In a background thread - keep window alive without blocking
                while self.window and self.window.winfo_exists():
                    try:
                        self.window.update()
                        self.window.after(50)  # 50ms delay
                    except tk.TclError:
                        break
        except Exception as e:
            print(f"Error in window loop: {e}")
    
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
        
        progress_text = tk.Text(progress_window, height=10, width=60)
        progress_text.pack(pady=10, padx=10)

        # Initial line so user sees activity immediately
        progress_text.insert(tk.END, "Preparing service installation...\n")
        progress_text.see(tk.END)
        try:
            progress_window.update_idletasks(); progress_window.update()
        except tk.TclError:
            pass
        
        def log_progress(msg):
            progress_text.insert(tk.END, msg + "\n")
            progress_text.see(tk.END)
            try:
                progress_window.update_idletasks()
                progress_window.update()
            except tk.TclError:
                pass
        
        def install_thread():
            try:
                # Find service executable
                service_exe = None
                # Determine common install directories for both x64 and x86 program files
                pf = os.environ.get("ProgramFiles") or "C:/Program Files"
                pf86 = os.environ.get("ProgramFiles(x86)") or "C:/Program Files (x86)"
                managed_nebula_pf = Path(pf) / "ManagedNebula" / "NebulaAgentService.exe"
                managed_nebula_pf86 = Path(pf86) / "ManagedNebula" / "NebulaAgentService.exe"

                search_paths = [
                    Path(sys.executable).parent / "NebulaAgentService.exe",
                    Path(__file__).parent / "NebulaAgentService.exe",
                    managed_nebula_pf,
                    managed_nebula_pf86,
                    Path(NEBULA_DIR) / "bin" / "NebulaAgentService.exe",
                ]
                
                log_progress("Searching for NebulaAgentService.exe...")
                for path in search_paths:
                    if path.exists():
                        service_exe = path
                        log_progress(f"Found: {path}")
                        break
                
                if not service_exe:
                    log_progress("WARNING: NebulaAgentService.exe not found in expected locations")
                    log_progress("Attempting fallback: Python-based service installation...")
                    log_progress("")
                    
                    # Try to find service.py in the source directory
                    service_py = None
                    py_search_paths = [
                        Path(__file__).parent / "service.py",
                        Path(sys.executable).parent / "service.py",
                        Path(NEBULA_DIR) / "service.py",
                    ]
                    
                    for path in py_search_paths:
                        if path.exists():
                            service_py = path
                            log_progress(f"Found service.py: {path}")
                            break
                    
                    if not service_py:
                        log_progress("ERROR: Neither NebulaAgentService.exe nor service.py found!")
                        messagebox.showerror(
                            "Service Files Not Found",
                            "Could not find service executable or Python source.\n\n"
                            "Searched for NebulaAgentService.exe in:\n" +
                            "\n".join(str(p) for p in search_paths) +
                            "\n\nSearched for service.py in:\n" +
                            "\n".join(str(p) for p in py_search_paths)
                        )
                        progress_window.destroy()
                        return
                    
                    # Use Python to install service
                    log_progress("")
                    log_progress("Installing via Python (fallback method)...")
                    install_cmd = [sys.executable, str(service_py), "install", "--startup", "auto"]
                    log_progress("Running: " + " ".join(install_cmd))
                    
                    try:
                        install_result = subprocess.run(
                            install_cmd,
                            capture_output=True,
                            text=True,
                            timeout=30,
                            cwd=str(service_py.parent)
                        )
                        if install_result.returncode != 0:
                            log_progress("STDOUT:\n" + install_result.stdout)
                            log_progress("STDERR:\n" + install_result.stderr)
                            log_progress("✗ Python service install failed")
                            messagebox.showerror(
                                "Installation Failed",
                                "Python service install failed.\n\n" + (install_result.stderr or install_result.stdout)
                            )
                            progress_window.destroy()
                            self._refresh_status()
                            return
                        
                        log_progress("✓ Service installed via Python")
                        log_progress("")
                        log_progress("Starting service...")
                        
                        start_cmd = ["sc", "start", "NebulaAgent"]
                        log_progress("Running: " + " ".join(start_cmd))
                        start_result = subprocess.run(start_cmd, capture_output=True, text=True, timeout=15)
                        
                        if start_result.returncode == 0:
                            import time as _t
                            for _i in range(10):
                                q = subprocess.run(["sc", "query", "NebulaAgent"], capture_output=True, text=True)
                                if "RUNNING" in q.stdout:
                                    log_progress("✓ Service started and running")
                                    messagebox.showinfo("Success", "Service installed and started via Python!")
                                    break
                                _t.sleep(1)
                            else:
                                log_progress("⚠ Service start timed out")
                                messagebox.showwarning("Partial Success", "Service installed but may not be running")
                        else:
                            log_progress("Start output:\n" + start_result.stdout)
                            if start_result.stderr:
                                log_progress("Start errors:\n" + start_result.stderr)
                            messagebox.showwarning("Partial Success", "Service installed but failed to start.\n\n" + (start_result.stderr or start_result.stdout))
                        
                        progress_window.destroy()
                        self._refresh_status()
                        return
                        
                    except Exception as e:
                        log_progress(f"✗ Exception during Python install: {e}")
                        import traceback
                        log_progress(traceback.format_exc())
                        messagebox.showerror("Installation Failed", f"Python service install exception:\n\n{e}")
                        progress_window.destroy()
                        self._refresh_status()
                        return
                
                log_progress("")
                log_progress("Checking for existing service...")
                
                # Check if service already exists
                check_cmd = ["sc", "query", "NebulaAgent"]
                log_progress(f"Running: {' '.join(check_cmd)}")
                check_result = subprocess.run(
                    check_cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if check_result.returncode == 0:
                    log_progress("Service already exists, removing...")
                    # Stop service if running
                    stop_cmd = ["sc", "stop", "NebulaAgent"]
                    log_progress(f"Running: {' '.join(stop_cmd)}")
                    subprocess.run(stop_cmd, capture_output=True, text=True, timeout=8)
                    # Wait a moment
                    import time
                    time.sleep(1)
                    # Delete service
                    delete_cmd = ["sc", "delete", "NebulaAgent"]
                    log_progress(f"Running: {' '.join(delete_cmd)}")
                    delete_result = subprocess.run(
                        delete_cmd,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if delete_result.returncode == 0:
                        log_progress("✓ Existing service removed")
                    time.sleep(1)  # Wait for service deletion to complete
                
                log_progress("")
                log_progress("Creating Windows Service (exe self-install)...")
                try:
                    # Use the service executable's own pywin32 command handling: NebulaAgentService.exe install
                    # win32serviceutil expects space-separated option value (no '=')
                    install_cmd = [str(service_exe), "install", "--startup", "auto"]
                    log_progress("Running: " + " ".join(install_cmd))
                    install_result = subprocess.run(
                        install_cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if install_result.returncode != 0:
                        log_progress("STDOUT:\n" + install_result.stdout)
                        log_progress("STDERR:\n" + install_result.stderr)
                        log_progress("✗ Failed to install service via executable")
                        messagebox.showerror(
                            "Installation Failed",
                            "Service executable install failed.\n\n" + (install_result.stderr or install_result.stdout)
                        )
                        progress_window.destroy()
                        self._refresh_status()
                        return
                    log_progress("✓ Service created successfully")
                    log_progress("")
                    log_progress("Starting service...")
                    start_cmd = ["sc", "start", "NebulaAgent"]
                    log_progress("Running: " + " ".join(start_cmd))
                    start_result = subprocess.run(
                        start_cmd,
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    if start_result.returncode != 0:
                        log_progress("STDOUT:\n" + start_result.stdout)
                        log_progress("STDERR:\n" + start_result.stderr)
                        log_progress("⚠ Warning: Service created but failed initial start")
                        # Retry once after short delay (sometimes files settle)
                        import time as _t
                        _t.sleep(2)
                        log_progress("Retrying start...")
                        retry_result = subprocess.run(
                            start_cmd,
                            capture_output=True,
                            text=True,
                            timeout=15
                        )
                        if retry_result.returncode != 0:
                            log_progress("Retry STDOUT:\n" + retry_result.stdout)
                            log_progress("Retry STDERR:\n" + retry_result.stderr)
                            # Offer debug mode run to surface errors
                            log_progress("Launching service in debug mode to capture output...")
                            debug_cmd = [str(service_exe), "debug"]
                            try:
                                debug_result = subprocess.run(
                                    debug_cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=30
                                )
                                log_progress("Debug Output (truncated):\n" + debug_result.stdout[:800])
                                if debug_result.stderr:
                                    log_progress("Debug Errors (truncated):\n" + debug_result.stderr[:800])
                            except Exception as _de:
                                log_progress(f"Debug run failed: {_de}")
                            messagebox.showwarning(
                                "Partial Success",
                                "Service installed but failed to start.\n\n" + (retry_result.stderr or retry_result.stdout)
                            )
                        else:
                            log_progress("✓ Service started successfully on retry")
                            messagebox.showinfo(
                                "Success",
                                "Windows Service installed and started successfully on retry!"
                            )
                    else:
                        # Poll until running or timeout
                        import time as _t
                        for _i in range(10):
                            q = subprocess.run(["sc", "query", "NebulaAgent"], capture_output=True, text=True)
                            if "RUNNING" in q.stdout:
                                log_progress("✓ Service reported RUNNING")
                                messagebox.showinfo(
                                    "Success",
                                    "Windows Service installed and started successfully!"
                                )
                                break
                            _t.sleep(1)
                        else:
                            log_progress("⚠ Service start pending timeout; launching debug mode snapshot")
                            debug_cmd = [str(service_exe), "debug"]
                            try:
                                debug_result = subprocess.run(
                                    debug_cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=30
                                )
                                log_progress("Debug Output (truncated):\n" + debug_result.stdout[:800])
                                if debug_result.stderr:
                                    log_progress("Debug Errors (truncated):\n" + debug_result.stderr[:800])
                            except Exception as _de:
                                log_progress(f"Debug run failed: {_de}")
                            messagebox.showwarning(
                                "Partial Success",
                                "Service installed but did not reach RUNNING state in time."
                            )
                except Exception as e_install:
                    log_progress(f"✗ Exception during install/start: {e_install}")
                    messagebox.showerror(
                        "Installation Failed",
                        f"Exception during service install/start:\n\n{e_install}"
                    )
                
                progress_window.destroy()
                # Refresh status without recreating window
                if self.window:
                    self._refresh_status()
                
            except subprocess.TimeoutExpired:
                log_progress(f"\nERROR: Command timed out")
                messagebox.showerror("Error", "Service installation timed out.\n\nThe sc command is not responding.")
                try:
                    progress_window.destroy()
                except:
                    pass
            except Exception as e:
                log_progress(f"\nERROR: {str(e)}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Error", f"Service installation failed:\n\n{str(e)}")
                try:
                    progress_window.destroy()
                except:
                    pass
        
        # Run installation synchronously (Tkinter not thread-safe for direct widget updates)
        log_progress("Installer task starting...")
        install_thread()
    
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
    
    def _uninstall_service(self):
        """Uninstall the Windows Service"""
        if not is_admin():
            messagebox.showerror(
                "Administrator Required",
                "Uninstalling the service requires administrator privileges.\n\n"
                "Please run this application as Administrator."
            )
            return
        
        try:
            # Stop if running
            subprocess.run(["sc", "stop", "NebulaAgent"], capture_output=True, text=True, timeout=8)
            # Delete service
            result = subprocess.run(["sc", "delete", "NebulaAgent"], capture_output=True, text=True, timeout=8)
            if result.returncode == 0:
                messagebox.showinfo("Success", "Service uninstalled successfully!")
                if self.window:
                    self._refresh_status()
            else:
                messagebox.showerror("Error", f"Failed to uninstall service:\n\n{result.stderr if result.stderr else result.stdout}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to uninstall service:\n\n{str(e)}")
    
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
        
        # Create config window
        self.config_window = ConfigWindow(on_save=on_save)
        
        # Tkinter needs to run in main thread on Windows, but pystray also needs main thread
        # Solution: Create window in separate thread with proper exception handling
        def show_with_error_handling():
            try:
                self.config_window.show()
            except Exception as e:
                print(f"Error showing config window: {e}")
                import traceback
                traceback.print_exc()
        
        thread = threading.Thread(target=show_with_error_handling, daemon=False)
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
