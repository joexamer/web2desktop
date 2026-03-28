import os
import sys
import platform
import json
import subprocess
import argparse
import shutil
import urllib.request
import tempfile
from html.parser import HTMLParser

class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.icons = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        elif tag == "link":
            attrs_dict = dict(attrs)
            rel = attrs_dict.get("rel", "").lower()
            if rel in ["icon", "shortcut icon", "apple-touch-icon", "apple-touch-icon-precomposed"]:
                href = attrs_dict.get("href")
                if not href:
                    return
                href = href.strip().rstrip('.')
                sizes = attrs_dict.get("sizes", "0x0").lower().split("x")
                try:
                    width = int(sizes[0])
                except (ValueError, IndexError):
                    width = 0
                self.icons.append({"href": href, "width": width, "rel": rel})

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title = data

    def get_best_icon(self, base_url):
        if not self.icons:
            return None
        sorted_icons = sorted(
            self.icons, 
            key=lambda x: (x['rel'] == 'apple-touch-icon', x['width']), 
            reverse=True
        )
        best_icon = sorted_icons[0]['href']
        if best_icon and not best_icon.startswith("http"):
            from urllib.parse import urljoin
            best_icon = urljoin(base_url, best_icon)
        return best_icon

def check_linux():
    if platform.system().lower() != "linux":
        print("[!] Error: This tool is now optimized for Linux only.")
        sys.exit(1)

def get_metadata(url):
    print(f"[*] Extracting metadata from {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
            parser = MetadataParser()
            parser.feed(content)
            return parser.title.strip() or "Web App", parser.get_best_icon(url)
    except Exception as e:
        print(f"[!] Warning: Could not extract metadata: {e}")
        return "Web App", None

def check_requirements():
    print("[*] Checking system requirements...")
    missing = []
    try:
        subprocess.run(["node", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[+] Node.js is installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[!] Node.js is MISSING.")
        missing.append("node")
    try:
        subprocess.run(["npm", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[+] npm is installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[!] npm is MISSING.")
        missing.append("npm")
    if missing:
        print("\n[!] Error: Missing requirements. Please run: sudo apt update && sudo apt install -y nodejs npm")
        return False
    return True

def generate_package_json(app_name, icon_path=None):
    builder_config = {
        "appId": f"com.web2desktop.{app_name.lower().replace(' ', '')}",
        "productName": app_name,
        "directories": { "output": "dist" },
        "linux": {
            "target": ["AppImage"],
            "category": "Utility"
        }
    }
    if icon_path:
        builder_config["icon"] = os.path.basename(icon_path)
    return {
        "name": app_name.lower().replace(" ", "-"),
        "version": "1.0.0",
        "description": f"Linux AppImage for {app_name}",
        "author": "Web2Desktop Tool",
        "main": "main.js",
        "scripts": {
            "start": "electron .",
            "installer": "electron-builder --linux"
        },
        "build": builder_config,
        "devDependencies": {
            "electron": "^28.0.0",
            "electron-builder": "^24.9.1"
        }
    }

def generate_main_js(url, app_name, width=1200, height=800, hide_menu=False, icon_path=None, 
                     dark_mode=False, inject_css=None, inject_js=None, hotkey=None):
    has_custom_icon = "true" if icon_path else "false"
    icon_filename = os.path.basename(icon_path) if icon_path else "null"
    app_id = app_name.lower().replace(" ", "-")
    
    css_content = ""
    if inject_css and os.path.exists(inject_css):
        with open(inject_css, 'r') as f:
            css_content = f.read().replace('`', '\\`').replace('$', '\\$')
            
    js_content = ""
    if inject_js and os.path.exists(inject_js):
        with open(inject_js, 'r') as f:
            js_content = f.read().replace('`', '\\`').replace('$', '\\$')

    dark_mode_script = ""
    if dark_mode:
        dark_mode_script = f"""
        const darkThemeCss = `
            html, body, div, section, nav, header, footer, main, aside {{
                background-color: #121212 !important;
                color: #e0e0e0 !important;
            }}
            * {{ border-color: #444 !important; }}
            a {{ color: #8ab4f8 !important; }}
        `;
        mainWindow.webContents.on('did-finish-load', () => {{
            mainWindow.webContents.insertCSS(darkThemeCss, {{ cssOrigin: 'user' }});
        }});
        """

    hotkey_script = ""
    if hotkey:
        hotkey_script = f"""
        globalShortcut.register('{hotkey}', () => {{
            if (mainWindow.isVisible()) {{
                mainWindow.hide();
            }} else {{
                mainWindow.show();
                mainWindow.focus();
            }}
        }});
        """

    return f"""
const {{ app, BrowserWindow, shell, Menu, dialog, globalShortcut, ipcMain }} = require('electron');
const path = require('path');
const fs = require('fs');
const {{ execSync }} = require('child_process');

let mainWindow;
let wizardWindow;
const configPath = path.join(app.getPath('userData'), 'config.json');
const desktopPath = path.join(app.getPath('home'), '.local/share/applications', '{app_id}.desktop');

function loadConfig() {{
  try {{
    if (fs.existsSync(configPath)) {{
      return JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    }}
  }} catch (e) {{}}
  return {{}};
}}

function saveConfig(config) {{
  try {{
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  }} catch (e) {{}}
}}

async function promptForIcon() {{
  const result = await dialog.showOpenDialog(null, {{
    title: 'Select App Icon',
    filters: [{{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'ico'] }}],
    properties: ['openFile']
  }});

  if (!result.canceled && result.filePaths.length > 0) {{
    const newIconPath = result.filePaths[0];
    const destPath = path.join(app.getPath('userData'), 'app-icon' + path.extname(newIconPath));
    fs.copyFileSync(newIconPath, destPath);
    const config = loadConfig();
    config.customIcon = destPath;
    saveConfig(config);
    return destPath;
  }}
  return null;
}}

function createDesktopEntry(iconPath) {{
  const appPath = process.env.APPIMAGE || process.execPath;
  const desktopFile = `[Desktop Entry]
Name={app_name}
Exec="${{appPath}}" %U
Terminal=false
Type=Application
Icon=${{iconPath || 'electron'}}
Categories=Utility;
Comment=Desktop application for {app_name}
Actions=Uninstall;

[Desktop Action Uninstall]
Name=Uninstall {app_name}
Exec="${{appPath}}" --uninstall
`;
  fs.mkdirSync(path.dirname(desktopPath), {{ recursive: true }});
  fs.writeFileSync(desktopPath, desktopFile);
  fs.chmodSync(desktopPath, '755');
}}

function pinToDash() {{
  try {{
    const desktopFileName = '{app_id}.desktop';
    const currentFavorites = execSync('gsettings get org.gnome.shell favorite-apps').toString().trim();
    if (currentFavorites.includes(desktopFileName)) return;
    
    let favoritesArray = eval(currentFavorites);
    favoritesArray.push(desktopFileName);
    const newFavorites = JSON.stringify(favoritesArray).replace(/"/g, "'");
    execSync(`gsettings set org.gnome.shell favorite-apps "${{newFavorites}}"`);
  }} catch (e) {{
    console.log('Could not pin to dash:', e.message);
  }}
}}

function handleUninstall() {{
  const choice = dialog.showMessageBoxSync({{
    type: 'warning',
    buttons: ['Cancel', 'Yes, Uninstall'],
    title: 'Confirm Uninstall',
    message: 'Are you sure you want to uninstall {app_name} and remove all its data?'
  }});

  if (choice === 1) {{
    try {{
      if (fs.existsSync(desktopPath)) fs.unlinkSync(desktopPath);
      
      try {{
        const desktopFileName = '{app_id}.desktop';
        const currentFavorites = execSync('gsettings get org.gnome.shell favorite-apps').toString().trim();
        let favoritesArray = eval(currentFavorites);
        const index = favoritesArray.indexOf(desktopFileName);
        if (index > -1) {{
          favoritesArray.splice(index, 1);
          const newFavorites = JSON.stringify(favoritesArray).replace(/"/g, "'");
          execSync(`gsettings set org.gnome.shell favorite-apps "${{newFavorites}}"`);
        }}
      }} catch (e) {{}}

      if (fs.existsSync(configPath)) fs.unlinkSync(configPath);
      
      dialog.showMessageBoxSync({{
        type: 'info',
        message: '{app_name} has been uninstalled. The data will be wiped and app will close.'
      }});
      
      app.quit();
    }} catch (e) {{
      dialog.showErrorBox('Uninstall Error', e.message);
    }}
  }} else {{
    app.quit();
  }}
}}

if (process.argv.includes('--uninstall')) {{
  app.whenReady().then(handleUninstall);
}} else {{
  ipcMain.on('relaunch-app', () => {{
    app.relaunch();
    app.exit();
  }});

  ipcMain.handle('pick-icon', async () => {{
    return await promptForIcon();
  }});

  ipcMain.handle('install-app', async (event, iconPath) => {{
    createDesktopEntry(iconPath);
    pinToDash();
    const config = loadConfig();
    config.installed = true;
    saveConfig(config);
    return true;
  }});

  function showWizard() {{
    wizardWindow = new BrowserWindow({{
      width: 600,
      height: 500,
      title: 'Install {app_name}',
      resizable: false,
      webPreferences: {{
        nodeIntegration: true,
        contextIsolation: false
      }}
    }});
    wizardWindow.loadFile(path.join(__dirname, 'wizard.html'));
    wizardWindow.setMenu(null);
  }}

  function createMenu() {{
    const template = [
      {{ label: 'Application', submenu: [
        {{ label: 'Reload', role: 'reload' }},
        {{ label: 'Toggle DevTools', role: 'toggleDevTools' }},
        {{ type: 'separator' }},
        {{ label: 'Quit', role: 'quit' }}
      ]}},
      {{ label: 'Settings', submenu: [
        {{ label: 'Change App Icon', click: async () => {{
            const newIcon = await promptForIcon();
            if (newIcon) {{
              createDesktopEntry(newIcon);
              app.relaunch();
              app.exit();
            }}
        }} }},
        {{ type: 'separator' }},
        {{ label: 'Reset Icon', click: () => {{
             const config = loadConfig();
             delete config.customIcon;
             saveConfig(config);
             createDesktopEntry(null);
             app.relaunch();
             app.exit();
        }}}}
      ]}}
    ];
    Menu.setApplicationMenu(Menu.buildFromTemplate(template));
  }}

  function createWindow() {{
    const config = loadConfig();
    const buildIcon = {has_custom_icon} ? path.join(__dirname, "{icon_filename}") : null;
    const currentIcon = config.customIcon || buildIcon;

    mainWindow = new BrowserWindow({{
      width: {width}, height: {height},
      title: "{app_name}",
      icon: currentIcon,
      show: false,
      webPreferences: {{ nodeIntegration: false, contextIsolation: true }}
    }});

    mainWindow.loadURL("{url}");
    if ({'true' if hide_menu else 'false'}) mainWindow.setMenu(null); else createMenu();

    mainWindow.once('ready-to-show', () => mainWindow.show());

    mainWindow.webContents.on('did-finish-load', () => {{
      {f"mainWindow.webContents.insertCSS(`{css_content}`);" if css_content else ""}
      {f"mainWindow.webContents.executeJavaScript(`{js_content}`);" if js_content else ""}
    }});

    {dark_mode_script}

    mainWindow.webContents.setWindowOpenHandler(({{ url }}) => {{
      if (!url.startsWith("{url}")) {{ shell.openExternal(url); return {{ action: 'deny' }}; }}
      return {{ action: 'allow' }};
    }});

    // Improved Offline Handling
     mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {{
       // Ignore ERR_ABORTED (-3), which often happens during redirects
       if (isMainFrame && errorCode !== -3) {{
         mainWindow.loadFile(path.join(__dirname, 'offline.html'));
       }}
     }});
  }}

  app.whenReady().then(() => {{
    const config = loadConfig();
    if (!config.installed) {{
      showWizard();
    }} else {{
      createWindow();
    }}
    {hotkey_script}
  }});

  app.on('window-all-closed', () => app.quit());
  app.on('will-quit', () => globalShortcut.unregisterAll());
}}
"""

def generate_offline_html(app_name):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{app_name} - Offline</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #f0f2f5; margin: 0; }}
        .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; }}
        .btn {{ display: inline-block; padding: 12px 24px; background: #0084ff; color: white; border-radius: 8px; cursor: pointer; text-decoration: none; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Connection Lost</h1>
        <p>Please check your internet connection.</p>
        <button class="btn" onclick="window.location.reload()">Retry</button>
    </div>
</body>
</html>
"""

def generate_wizard_html(app_name):
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Install {app_name}</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #f8f9fa; margin: 0; display: flex; align-items: center; justify-content: center; height: 100vh; }}
        .container {{ background: white; width: 100%; height: 100%; padding: 40px; box-sizing: border-box; display: flex; flex-direction: column; }}
        h1 {{ margin: 0 0 10px 0; font-size: 24px; }}
        p {{ color: #6c757d; font-size: 14px; margin-bottom: 30px; }}
        .icon-preview {{ width: 128px; height: 128px; background: #e9ecef; border-radius: 20px; align-self: center; display: flex; align-items: center; justify-content: center; margin-bottom: 20px; overflow: hidden; }}
        .icon-preview img {{ width: 100%; height: 100%; object-fit: cover; }}
        .btn-group {{ margin-top: auto; display: flex; justify-content: flex-end; gap: 10px; }}
        .btn {{ padding: 10px 20px; border-radius: 6px; border: none; cursor: pointer; font-weight: 600; font-size: 14px; transition: 0.2s; }}
        .btn-secondary {{ background: #e9ecef; color: #495057; }}
        .btn-primary {{ background: #007bff; color: white; }}
        .btn:hover {{ opacity: 0.9; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Install {app_name}</h1>
        <p>This will add the application to your Linux menu and pin it to your dash so you can open it easily anytime.</p>
        
        <div class="icon-preview" id="icon-preview">
            <span>No Icon Selected</span>
        </div>
        
        <button class="btn btn-secondary" onclick="pickIcon()" style="width: 200px; align-self: center;">Choose Application Icon</button>

        <div class="btn-group">
            <button class="btn btn-secondary" onclick="window.close()">Cancel</button>
            <button class="btn btn-primary" onclick="install()">Install & Launch</button>
        </div>
    </div>

    <script>
        const {{ ipcRenderer }} = require('electron');
        let selectedIcon = null;

        async function pickIcon() {{
            const path = await ipcRenderer.invoke('pick-icon');
            if (path) {{
                selectedIcon = path;
                document.getElementById('icon-preview').innerHTML = `<img src="${{path}}">`;
            }}
        }}

        async function install() {{
            await ipcRenderer.invoke('install-app', selectedIcon);
            ipcRenderer.send('relaunch-app');
        }}
    </script>
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(description="Professional Web-to-Desktop Converter (Linux Only)")
    parser.add_argument("url", nargs="?", help="URL to convert")
    parser.add_argument("name", nargs="?", help="App name")
    parser.add_argument("--out", default=".", help="Output directory")
    parser.add_argument("--icon", help="App icon path (PNG)")
    parser.add_argument("--hide-menu", action="store_true", help="Hide menu bar")
    parser.add_argument("--width", type=int, default=1200, help="Initial width")
    parser.add_argument("--height", type=int, default=800, help="Initial height")
    parser.add_argument("--dark-mode", action="store_true", help="Force dark mode styling")
    parser.add_argument("--inject-css", help="CSS file to inject")
    parser.add_argument("--inject-js", help="JS file to inject")
    parser.add_argument("--hotkey", help="Global toggle hotkey (e.g. Alt+Shift+A)")
    
    args = parser.parse_args()
    check_linux()
    if not check_requirements(): sys.exit(1)
    if not args.url:
        print("\n[!] No URL provided.")
        sys.exit(1)

    extracted_name, best_icon_url = get_metadata(args.url)
    app_name = args.name or extracted_name
    print(f"[*] App Name: {app_name}")

    with tempfile.TemporaryDirectory() as build_dir:
        print(f"[*] Preparing build...")
        icon_path = args.icon
        if not icon_path and best_icon_url:
            try:
                icon_ext = os.path.splitext(best_icon_url.split('?')[0])[1] or ".png"
                icon_path = os.path.join(build_dir, f"icon{icon_ext}")
                req = urllib.request.Request(best_icon_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    with open(icon_path, 'wb') as out_file: out_file.write(response.read())
            except Exception: icon_path = None

        final_icon_path = None
        if icon_path and os.path.exists(icon_path):
            final_icon_path = os.path.join(build_dir, "icon" + os.path.splitext(icon_path)[1])
            if os.path.abspath(icon_path) != os.path.abspath(final_icon_path):
                shutil.copy2(icon_path, final_icon_path)

        with open(os.path.join(build_dir, "package.json"), "w") as f:
            json.dump(generate_package_json(app_name, final_icon_path), f, indent=2)
        with open(os.path.join(build_dir, "main.js"), "w") as f:
            f.write(generate_main_js(args.url, app_name, args.width, args.height, args.hide_menu, final_icon_path,
                                     dark_mode=args.dark_mode, inject_css=args.inject_css, inject_js=args.inject_js, hotkey=args.hotkey))
        with open(os.path.join(build_dir, "offline.html"), "w") as f:
            f.write(generate_offline_html(app_name))
        with open(os.path.join(build_dir, "wizard.html"), "w") as f:
            f.write(generate_wizard_html(app_name))

        print("[*] Building AppImage...")
        try:
            subprocess.run(["npm", "install"], cwd=build_dir, check=True)
            result = subprocess.run(["npm", "run", "installer"], cwd=build_dir, capture_output=True, text=True)
            if result.returncode != 0:
                combined_log = (result.stdout or "") + (result.stderr or "")
                if "must be at least 256x256" in combined_log:
                    print("[!] Icon too small. Retrying without icon...")
                    with open(os.path.join(build_dir, "package.json"), "r") as f: pkg = json.load(f)
                    if "icon" in pkg["build"]: del pkg["build"]["icon"]
                    with open(os.path.join(build_dir, "package.json"), "w") as f: json.dump(pkg, f, indent=2)
                    for f in os.listdir(build_dir):
                        if f.startswith("icon."): os.remove(os.path.join(build_dir, f))
                    subprocess.run(["npm", "run", "installer"], cwd=build_dir, check=True)
                else:
                    print(f"\n[!] Build failed:\n{combined_log}"); sys.exit(1)
            dist_dir = os.path.join(build_dir, "dist")
            for f in os.listdir(dist_dir):
                if f.endswith(".AppImage") and "latest" not in f.lower():
                    final_dest = os.path.join(os.path.abspath(args.out), f)
                    shutil.move(os.path.join(dist_dir, f), final_dest)
                    print(f"\n[!] SUCCESS! AppImage ready at: {final_dest}")
                    break
        except Exception as e: print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()
