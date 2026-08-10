import os
import time
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from pywinauto import Desktop, Application
    from pywinauto.findwindows import ElementNotFoundError
except ImportError:
    Desktop = None
    Application = None
    ElementNotFoundError = Exception

logger = logging.getLogger(__name__)

def find_executable(app_name: str) -> Optional[str]:
    """Attempt to find the executable path for a given application name."""
    app_name_lower = app_name.lower()
    
    # Common hardcoded fallbacks
    common_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        r"C:\Windows\System32\notepad.exe",
        r"C:\Windows\explorer.exe"
    ]
    
    for path in common_paths:
        if app_name_lower in path.lower() and os.path.exists(path):
            return path
            
    # Search Start Menu
    start_menu_paths = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
    ]
    
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
    except ImportError:
        shell = None
    
    if shell:
        for menu_path in start_menu_paths:
            if not os.path.exists(menu_path):
                continue
            for root, _, files in os.walk(menu_path):
                for file in files:
                    if file.endswith(".lnk") and app_name_lower in file.lower():
                        shortcut_path = os.path.join(root, file)
                        try:
                            shortcut = shell.CreateShortCut(shortcut_path)
                            target = shortcut.Targetpath
                            if target and os.path.exists(target) and target.lower().endswith(".exe"):
                                return target
                        except Exception:
                            pass
                        
    return None

def launch_application(app_name: str) -> Dict[str, Any]:
    """Launch an application and wait for it to appear."""
    executable = find_executable(app_name)
    if not executable:
        # Fallback to shell execution for things in PATH (like 'notepad' or 'explorer')
        try:
            subprocess.Popen(app_name, shell=True)
            return {"success": True, "application": app_name, "message": f"Launched via shell"}
        except Exception as e:
            return {"success": False, "error": f"Could not find or launch {app_name}: {e}"}
            
    try:
        subprocess.Popen([executable])
        # Wait a moment for window to appear
        time.sleep(2.0)
        return {"success": True, "application": app_name, "path": executable}
    except Exception as e:
        return {"success": False, "error": str(e)}

def focus_window(title_keyword: str) -> Dict[str, Any]:
    """Focus a window containing the keyword in its title."""
    if not Desktop:
        return {"success": False, "error": "pywinauto not installed."}
        
    try:
        windows = Desktop(backend="uia").windows()
        for win in windows:
            if title_keyword.lower() in win.window_text().lower():
                win.set_focus()
                return {"success": True, "window": win.window_text()}
        return {"success": False, "error": f"No window found matching '{title_keyword}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def type_text(text: str, window_keyword: Optional[str] = None) -> Dict[str, Any]:
    """Type text into the focused window."""
    if not Desktop:
        return {"success": False, "error": "pywinauto not installed."}
        
    if window_keyword:
        res = focus_window(window_keyword)
        if not res["success"]:
            return res
            
    try:
        import pywinauto.keyboard as keyboard
        # Replace spaces with {SPACE} for pywinauto
        formatted_text = text.replace(" ", "{SPACE}")
        keyboard.send_keys(formatted_text)
        return {"success": True, "typed": text}
    except Exception as e:
        return {"success": False, "error": str(e)}

def click_element(description: str, window_keyword: Optional[str] = None) -> Dict[str, Any]:
    """Attempt to click an element by name using UIA."""
    if not Desktop:
        return {"success": False, "error": "pywinauto not installed."}
        
    try:
        if window_keyword:
            windows = Desktop(backend="uia").windows()
            target_win = None
            for win in windows:
                if window_keyword.lower() in win.window_text().lower():
                    target_win = win
                    break
            if not target_win:
                return {"success": False, "error": f"No window found matching '{window_keyword}'"}
                
            element = target_win.child_window(title_re=f".*{description}.*", found_index=0)
            element.click_input()
            return {"success": True, "element": description}
        else:
            return {"success": False, "error": "Window keyword required for clicking elements via UIA."}
    except ElementNotFoundError:
        return {"success": False, "error": f"UI element '{description}' not found. Consider using look_at_screen fallback."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_hotkey(keys: str, window_keyword: Optional[str] = None) -> Dict[str, Any]:
    """Send a keyboard shortcut or specific key like {SPACE} or ^l."""
    if not Desktop:
        return {"success": False, "error": "pywinauto not installed."}
        
    if window_keyword:
        res = focus_window(window_keyword)
        if not res["success"]:
            return res
            
    try:
        import pywinauto.keyboard as keyboard
        keyboard.send_keys(keys)
        return {"success": True, "hotkey": keys}
    except Exception as e:
        return {"success": False, "error": str(e)}
