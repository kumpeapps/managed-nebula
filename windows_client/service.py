"""
Managed Nebula Windows Service
Runs the Nebula agent as a Windows Service using pywin32
"""

import logging
import os
import socket
import sys
import threading
import time
from pathlib import Path

# Windows-specific imports
try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError:
    print("Error: pywin32 is required. Install with: pip install pywin32")
    sys.exit(1)

# Import agent components
from agent import (
    __version__,
    ensure_directories,
    run_once,
    restart_nebula,
    is_nebula_running,
    start_nebula,
    stop_nebula,
    setup_logging,
    NEBULA_DIR,
    LOG_DIR,
)
from config import load_config

# Force-load http client stack so PyInstaller bundles dynamic modules
try:
    import httpx  # noqa: F401
    import httpcore  # noqa: F401
    import httpcore._backends.base  # noqa: F401
    import httpcore._backends.sync  # noqa: F401
    import httpcore._backends.auto  # noqa: F401
    import httpcore._async.connection  # noqa: F401
    import httpcore._async.connection_pool  # noqa: F401
    import httpcore._async.http11  # noqa: F401
    import httpcore._async.http_proxy  # noqa: F401
    import httpcore._async.socks_proxy  # noqa: F401
    import httpcore._sync.connection  # noqa: F401
    import httpcore._sync.connection_pool  # noqa: F401
    import httpcore._sync.http11  # noqa: F401
    import httpcore._sync.http_proxy  # noqa: F401
    import httpcore._sync.socks_proxy  # noqa: F401
    import h11  # noqa: F401
except Exception:
    # Defer any import errors to runtime diagnostics/CLI
    pass


class NebulaAgentService(win32serviceutil.ServiceFramework):
    """
    Windows Service wrapper for Managed Nebula Agent
    
    The service runs in a polling loop, fetching configuration from the server
    and managing the Nebula daemon.
    """
    
    _svc_name_ = "NebulaAgent"
    _svc_display_name_ = "Managed Nebula Agent"
    _svc_description_ = (
        "Managed Nebula VPN Agent - Polls server for configuration "
        "and manages the local Nebula daemon"
    )
    
    # CRITICAL: For PyInstaller frozen executables, explicitly tell pywin32
    # where the service executable is located
    # Without this, HandleCommandLine fails to register the service properly
    _exe_name_ = sys.executable if getattr(sys, 'frozen', False) else None
    _exe_args_ = None  # No additional arguments needed for the service executable
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        
        # Create stop event
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        
        # Thread control
        self._stop_requested = False
        self._worker_thread = None
        
        # Setup logging
        ensure_directories()
        self.logger = setup_logging()
        
        socket.setdefaulttimeout(60)
    
    def SvcStop(self):
        """Handle service stop request"""
        self.logger.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        # Signal stop
        self._stop_requested = True
        win32event.SetEvent(self.hWaitStop)
        
        # Stop Nebula daemon
        try:
            stop_nebula()
        except Exception as e:
            self.logger.error("Error stopping Nebula: %s", e)
    
    def SvcDoRun(self):
        """Main service entry point"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )
        
        self.logger.info("Service starting (v%s)", __version__)
        
        try:
            self.main()
        except Exception as e:
            self.logger.error("Service error: %s", e)
            servicemanager.LogErrorMsg(f"Service error: {e}")
    
    def main(self):
        """Main service loop"""
        config = load_config()
        poll_interval_hours = config.get("poll_interval_hours", 24)
        poll_interval_seconds = poll_interval_hours * 3600
        
        self.logger.info(
            "Starting polling loop (interval: %d hours)",
            poll_interval_hours
        )
        
        # Initial run
        self._do_config_fetch()
        
        # Start Nebula if configured
        if config.get("auto_start_nebula", True):
            if not is_nebula_running():
                start_nebula()
        
        # Main loop
        while not self._stop_requested:
            # Wait for stop event or timeout
            wait_result = win32event.WaitForSingleObject(
                self.hWaitStop,
                poll_interval_seconds * 1000  # Convert to milliseconds
            )
            
            if wait_result == win32event.WAIT_OBJECT_0:
                # Stop event signaled
                break
            
            # Timeout occurred, do another config fetch
            self._do_config_fetch()
        
        self.logger.info("Service stopped")
    
    def _do_config_fetch(self):
        """Perform configuration fetch and update"""
        try:
            self.logger.info("Fetching configuration...")
            run_once(restart_on_change=True)
            self.logger.info("Configuration fetch complete")
        except Exception as e:
            self.logger.error("Configuration fetch failed: %s", e)


def install_service(
    username: str = None,
    password: str = None,
    startup: str = "auto"
):
    """Install the service"""
    try:
        # Get the path to this script
        script_path = os.path.abspath(__file__)
        
        # Build command line
        args = ["install"]
        
        if startup == "auto":
            args.append("--startup=auto")
        elif startup == "manual":
            args.append("--startup=manual")
        elif startup == "delayed":
            args.append("--startup=delayed")
        
        if username:
            args.extend(["--username", username])
            if password:
                args.extend(["--password", password])
        
        win32serviceutil.HandleCommandLine(NebulaAgentService, argv=args)
        print(f"Service '{NebulaAgentService._svc_name_}' installed successfully")
        return True
    except Exception as e:
        print(f"Failed to install service: {e}")
        return False


def uninstall_service():
    """Uninstall the service"""
    try:
        # Stop service first if running
        try:
            win32serviceutil.StopService(NebulaAgentService._svc_name_)
        except Exception:
            pass
        
        win32serviceutil.RemoveService(NebulaAgentService._svc_name_)
        print(f"Service '{NebulaAgentService._svc_name_}' uninstalled successfully")
        return True
    except Exception as e:
        print(f"Failed to uninstall service: {e}")
        return False


def start_service():
    """Start the service"""
    try:
        win32serviceutil.StartService(NebulaAgentService._svc_name_)
        print(f"Service '{NebulaAgentService._svc_name_}' started")
        return True
    except Exception as e:
        print(f"Failed to start service: {e}")
        return False


def stop_service():
    """Stop the service"""
    try:
        win32serviceutil.StopService(NebulaAgentService._svc_name_)
        print(f"Service '{NebulaAgentService._svc_name_}' stopped")
        return True
    except Exception as e:
        print(f"Failed to stop service: {e}")
        return False


def get_service_status() -> str:
    """Get service status"""
    try:
        status = win32serviceutil.QueryServiceStatus(
            NebulaAgentService._svc_name_
        )
        state = status[1]
        
        status_map = {
            win32service.SERVICE_STOPPED: "Stopped",
            win32service.SERVICE_START_PENDING: "Starting",
            win32service.SERVICE_STOP_PENDING: "Stopping",
            win32service.SERVICE_RUNNING: "Running",
            win32service.SERVICE_CONTINUE_PENDING: "Continuing",
            win32service.SERVICE_PAUSE_PENDING: "Pausing",
            win32service.SERVICE_PAUSED: "Paused",
        }
        
        return status_map.get(state, f"Unknown ({state})")
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    # Debug: Log command line for troubleshooting (filter it out before passing to pywin32)
    debug_cli = False
    if "--debug-cli" in sys.argv:
        debug_cli = True
        print(f"DEBUG: sys.argv (original) = {sys.argv}", file=sys.stderr)
        sys.argv = [arg for arg in sys.argv if arg != "--debug-cli"]
        print(f"DEBUG: sys.argv (filtered) = {sys.argv}", file=sys.stderr)
        print(f"DEBUG: len(sys.argv) = {len(sys.argv)}", file=sys.stderr)
        print(f"DEBUG: frozen = {getattr(sys, 'frozen', False)}", file=sys.stderr)
    
    if len(sys.argv) == 1:
        # Running as service
        try:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(NebulaAgentService)
            servicemanager.StartServiceCtrlDispatcher()
        except win32service.error as e:
            # Not running as service, show help
            print("Managed Nebula Agent Service")
            print("=" * 40)
            print()
            print("Usage:")
            print("  python service.py install   - Install the service")
            print("  python service.py start     - Start the service")
            print("  python service.py stop      - Stop the service")
            print("  python service.py remove    - Uninstall the service")
            print("  python service.py status    - Show service status")
            print("  python service.py debug     - Run in debug mode (console)")
            print()
            print("Service Management (PowerShell):")
            print("  Start-Service NebulaAgent")
            print("  Stop-Service NebulaAgent")
            print("  Get-Service NebulaAgent")
    elif sys.argv[1].lower() == "debug":
        # Run service in console mode for debugging
        print("Running service in debug mode (console)...")
        print("Press Ctrl+C to stop")
        service = NebulaAgentService([])
        service.SvcDoRun()
    elif sys.argv[1].lower() == "status":
        print(f"Service Status: {get_service_status()}")
    elif sys.argv[1].lower() == "version":
        print(f"Managed Nebula Agent Service v{__version__}")
        print(f"Python: {sys.version}")
        # Try to detect if running from PyInstaller bundle
        if getattr(sys, 'frozen', False):
            print(f"Build: PyInstaller bundle (frozen)")
            print(f"Executable: {sys.executable}")
        else:
            print(f"Build: Running from Python source")
        # Check for httpx to verify dependencies
        try:
            import httpx
            print(f"httpx: {httpx.__version__}")
        except ImportError:
            print("httpx: NOT FOUND (service will fail)")
        sys.exit(0)
    elif sys.argv[1].lower() == "install":
        # Handle install command directly to avoid pywin32 argument parsing issues
        print(f"Installing {NebulaAgentService._svc_display_name_}...")
        
        # Parse startup mode from command line
        startup_mode = win32service.SERVICE_DEMAND_START  # default: manual
        for i, arg in enumerate(sys.argv):
            if arg in ("--startup", "--startup=auto", "--startup=delayed", "--startup=disabled"):
                if arg == "--startup" and i + 1 < len(sys.argv):
                    startup_value = sys.argv[i + 1].lower()
                elif "=" in arg:
                    startup_value = arg.split("=", 1)[1].lower()
                else:
                    continue
                    
                if startup_value == "auto":
                    startup_mode = win32service.SERVICE_AUTO_START
                elif startup_value == "delayed":
                    startup_mode = win32service.SERVICE_AUTO_START  # Will set delayed after
                elif startup_value == "disabled":
                    startup_mode = win32service.SERVICE_DISABLED
                break
        
        try:
            # Use the executable path for frozen apps, or Python + script path for source
            exe_path = sys.executable if getattr(sys, 'frozen', False) else None
            exe_args = None
            
            if debug_cli:
                print(f"DEBUG: exe_path = {exe_path}", file=sys.stderr)
                print(f"DEBUG: startup_mode = {startup_mode}", file=sys.stderr)
            
            # Install the service
            win32serviceutil.InstallService(
                pythonClassString=f"{__name__}.{NebulaAgentService.__name__}",
                serviceName=NebulaAgentService._svc_name_,
                displayName=NebulaAgentService._svc_display_name_,
                startType=startup_mode,
                description=NebulaAgentService._svc_description_,
                exeName=exe_path,
                exeArgs=exe_args
            )
            print(f"✓ Service '{NebulaAgentService._svc_name_}' installed successfully")
            print(f"  Startup mode: {['Manual', 'Auto', 'Disabled'][startup_mode - 2]}")
            sys.exit(0)
        except Exception as e:
            print(f"✗ Failed to install service: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    elif sys.argv[1].lower() in ("remove", "uninstall"):
        # Handle remove command directly
        print(f"Removing {NebulaAgentService._svc_display_name_}...")
        try:
            win32serviceutil.RemoveService(NebulaAgentService._svc_name_)
            print(f"✓ Service '{NebulaAgentService._svc_name_}' removed successfully")
            sys.exit(0)
        except Exception as e:
            print(f"✗ Failed to remove service: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif sys.argv[1].lower() == "start":
        # Handle start command directly
        print(f"Starting {NebulaAgentService._svc_display_name_}...")
        try:
            win32serviceutil.StartService(NebulaAgentService._svc_name_)
            print(f"✓ Service '{NebulaAgentService._svc_name_}' started successfully")
            sys.exit(0)
        except Exception as e:
            print(f"✗ Failed to start service: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif sys.argv[1].lower() == "stop":
        # Handle stop command directly
        print(f"Stopping {NebulaAgentService._svc_display_name_}...")
        try:
            win32serviceutil.StopService(NebulaAgentService._svc_name_)
            print(f"✓ Service '{NebulaAgentService._svc_name_}' stopped successfully")
            sys.exit(0)
        except Exception as e:
            print(f"✗ Failed to stop service: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        # Fallback to HandleCommandLine for other commands (update, restart, etc)
        try:
            if debug_cli:
                print(f"DEBUG: Calling HandleCommandLine for command: {sys.argv[1]}", file=sys.stderr)
            win32serviceutil.HandleCommandLine(NebulaAgentService)
        except Exception as e:
            print(f"Error handling command '{sys.argv[1]}': {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
