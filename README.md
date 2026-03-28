# Web2Desktop 🚀

Convert any website into a professional Linux desktop application (AppImage) with a single command.

Web2Desktop is a powerful Python CLI tool that uses Electron to wrap websites into standalone executables. It's designed specifically for Linux, offering deep system integration, a professional install wizard, and advanced customization options.

## ✨ Features

- **📦 One-File Output**: Generates a single `.AppImage` file that runs anywhere on Linux.
- **🧙 Install Wizard**: The generated app includes a professional first-run installer that integrates the app into your system menu.
- **🖼️ Smart Metadata**: Automatically extracts the website's title and highest-resolution icon (favicon/apple-touch-icon).
- **🛠️ System Integration**:
    - **Pin to Dash**: Automatically pins the app to your GNOME taskbar upon installation.
    - **Right-Click Uninstall**: Standard Linux desktop menu action to completely remove the app and its data.
- **🎨 Advanced Customization**:
    - **Dark Mode**: Force a modern dark theme on any website with `--dark-mode`.
    - **CSS/JS Injection**: Inject your own styles and scripts to modify website behavior.
    - **Global Hotkeys**: Set a system-wide shortcut (e.g., `Alt+Shift+G`) to toggle the app's visibility.
- **📶 Robust Offline Mode**: Professional "Connection Lost" page with automatic recovery.
- **🧹 Zero Clutter**: All build processes happen in temporary directories and are cleaned up automatically.

## 📋 Requirements

Before using Web2Desktop, ensure you have the following installed:

- **Python 3.10+**
- **Node.js & npm** (The tool will check for these and provide installation commands if missing)

## 🚀 Installation

Clone this repository to your local machine:

```bash
git clone https://github.com/your-username/web-to-desktop.git
cd web-to-desktop
```

## 📖 Usage

### Basic Usage
Convert a website using only its URL. The tool will automatically find the name and icon.
```bash
python3 web2desktop.py "https://www.youtube.com"
```

### Advanced Usage
Customize the name, icon, and behavior:
```bash
python3 web2desktop.py "https://www.google.com" "Google Pro" \
    --dark-mode \
    --hotkey "Alt+Shift+G" \
    --width 1400 \
    --height 900
```

### Full CLI Options
| Option | Description |
| :--- | :--- |
| `url` | The URL of the website to convert (required). |
| `name` | The name of the desktop application (optional). |
| `--icon` | Path to a custom PNG icon. |
| `--out` | Output directory for the final AppImage (default: `.`). |
| `--dark-mode` | Force a modern dark theme on the website. |
| `--inject-css` | Path to a CSS file to inject into the app. |
| `--inject-js` | Path to a JS file to inject into the app. |
| `--hotkey` | Global toggle hotkey (e.g., `Alt+Shift+A`). |
| `--hide-menu` | Hide the top menu bar by default. |
| `--width` / `--height`| Set initial window dimensions (default: 1200x800). |

## 🛠️ How It Works

1. **Metadata Scraper**: Uses a custom HTML parser to find the best title and highest-resolution icon available on the site.
2. **Template Engine**: Generates a professional Electron project with custom logic for system integration and offline handling.
3. **Build Engine**: Uses `electron-builder` to compile the source into a high-compression `.AppImage`.
4. **Cleanup**: Automatically wipes all temporary source files, leaving you with only the final launcher.

## 🤝 Contributing

Feel free to open issues or submit pull requests to help improve the tool!

## 📜 License

 GNU GENERAL PUBLIC LICENSE - feel free to use it for your own projects!
