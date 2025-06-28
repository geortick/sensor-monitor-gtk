#!/bin/bash

# System Sensor Monitor GTK Installation Script

set -e

echo "🌡️  System Sensor Monitor GTK Installer"
echo "========================================"

# Detect distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    echo "❌ Cannot detect Linux distribution"
    exit 1
fi

echo "📋 Detected distribution: $PRETTY_NAME"

# Install dependencies based on distribution
echo "📦 Installing dependencies..."

case $DISTRO in
    "fedora"|"rhel"|"centos")
        sudo dnf install -y python3 python3-gobject gtk4 libadwaita lm-sensors
        ;;
    "ubuntu"|"debian")
        sudo apt update
        sudo apt install -y python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 lm-sensors
        ;;
    "arch"|"manjaro")
        sudo pacman -S --needed python python-gobject gtk4 libadwaita lm_sensors
        ;;
    "opensuse"|"opensuse-leap"|"opensuse-tumbleweed")
        sudo zypper install -y python3 python3-gobject typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1 sensors
        ;;
    *)
        echo "⚠️  Unsupported distribution: $DISTRO"
        echo "Please install the following packages manually:"
        echo "- Python 3.7+"
        echo "- PyGObject (python3-gobject)"
        echo "- GTK4 with GObject introspection"
        echo "- libadwaita with GObject introspection"
        echo "- lm-sensors"
        ;;
esac

# Make script executable
echo "🔧 Setting up application..."
chmod +x sensor_monitor.py

# Test dependencies
echo "🧪 Testing dependencies..."

python3 -c "import gi; gi.require_version('Gtk', '4.0'); print('✅ GTK4 OK')" 2>/dev/null || {
    echo "❌ GTK4 not properly installed"
    exit 1
}

python3 -c "import gi; gi.require_version('Adw', '1'); print('✅ Adwaita OK')" 2>/dev/null || {
    echo "❌ libadwaita not properly installed"
    exit 1
}

which sensors >/dev/null 2>&1 && echo "✅ lm-sensors OK" || {
    echo "❌ lm-sensors not found"
    exit 1
}

# Check if sensors need to be detected
if ! sensors >/dev/null 2>&1; then
    echo "🔍 Sensors not detected. Running sensor detection..."
    echo "⚠️  This may require answering some questions."
    sudo sensors-detect
fi

# Optional: Install desktop file
read -p "📱 Install desktop file for application menu? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    DESKTOP_DIR="$HOME/.local/share/applications"
    mkdir -p "$DESKTOP_DIR"
    
    # Update desktop file with absolute path
    sed "s|Exec=python3 sensor_monitor.py|Exec=python3 $(pwd)/sensor_monitor.py|" sensor-monitor.desktop > "$DESKTOP_DIR/sensor-monitor.desktop"
    
    # Update desktop database
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$DESKTOP_DIR"
    fi
    
    echo "✅ Desktop file installed to $DESKTOP_DIR"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "🚀 To run the application:"
echo "   python3 sensor_monitor.py"
echo ""
echo "📚 For more information, see README.md"
