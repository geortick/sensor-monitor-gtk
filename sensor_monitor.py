#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk
import subprocess
import re
import math

class SensorCard(Gtk.Box):
    def __init__(self, title, adapter, icon_name=""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_size_request(220, 140)
        self.add_css_class("card")
        self.add_css_class("sensor-card")
        
        # Header with icon and title
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(20)
            header.append(icon)
        
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("title-4")
        title_label.set_xalign(0)
        title_label.set_ellipsize(3)  # Ellipsize end
        header.append(title_label)
        
        self.append(header)
        
        # Adapter label
        adapter_label = Gtk.Label(label=adapter)
        adapter_label.add_css_class("caption")
        adapter_label.set_xalign(0)
        adapter_label.set_ellipsize(3)
        self.append(adapter_label)
        
        # Value container
        self.value_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.append(self.value_box)

    def add_value(self, name, value, unit=""):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_halign(Gtk.Align.FILL)
        
        # Name label
        name_label = Gtk.Label(label=name)
        name_label.set_xalign(0)
        name_label.set_hexpand(True)
        name_label.add_css_class("caption")
        row.append(name_label)
        
        # Value with color coding
        value_text = f"{value:.1f}{unit}" if unit else f"{value:.0f}"
        value_label = Gtk.Label(label=value_text)
        value_label.set_xalign(1)
        value_label.add_css_class("heading")
        
        # Color code based on value type and range
        if unit == "°C":
            if value > 80:
                value_label.add_css_class("error")
            elif value > 60:
                value_label.add_css_class("warning")
            else:
                value_label.add_css_class("success")
        elif unit == " RPM":
            value_label.add_css_class("accent")
        elif unit == "V":
            value_label.add_css_class("success")
        
        row.append(value_label)
        self.value_box.append(row)

    def clear_values(self):
        child = self.value_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.value_box.remove(child)
            child = next_child

class CircularProgress(Gtk.DrawingArea):
    def __init__(self, size=80):
        super().__init__()
        self.set_size_request(size, size)
        self.set_draw_func(self._draw)
        self.progress = 0.0
        self.max_value = 100.0
        self.current_value = 0.0
        self.label_text = "0°C"
        self.color = (0.2, 0.7, 0.9)  # Default blue
    
    def set_value(self, value, max_val=100.0, label="", color=None):
        self.current_value = value
        self.max_value = max_val
        self.progress = min(value / max_val, 1.0) if max_val > 0 else 0
        self.label_text = label or f"{value:.1f}"
        
        # Auto color based on temperature
        if color:
            self.color = color
        elif "°C" in label:
            temp = value
            if temp > 80:
                self.color = (0.9, 0.2, 0.2)  # Red
            elif temp > 60:
                self.color = (0.9, 0.6, 0.2)  # Orange
            else:
                self.color = (0.2, 0.7, 0.2)  # Green
        
        self.queue_draw()
    
    def _draw(self, area, cr, width, height, user_data=None):
        center_x, center_y = width / 2, height / 2
        radius = min(width, height) / 2 - 12
        
        # Background circle - darker and more visible
        cr.set_line_width(10)
        cr.set_source_rgba(0.1, 0.1, 0.1, 0.8)  # Much darker background
        cr.arc(center_x, center_y, radius, 0, 2 * math.pi)
        cr.stroke()
        
        # Progress arc - thicker and more vibrant
        if self.progress > 0:
            cr.set_line_width(10)
            cr.set_source_rgba(*self.color, 1.0)
            start_angle = -math.pi / 2  # Start from top
            end_angle = start_angle + (2 * math.pi * self.progress)
            cr.arc(center_x, center_y, radius, start_angle, end_angle)
            cr.stroke()
        
        # Center background circle for better text readability
        cr.set_source_rgba(0.05, 0.05, 0.05, 0.9)  # Dark background for text
        cr.arc(center_x, center_y, radius * 0.6, 0, 2 * math.pi)
        cr.fill()
        
        # Center text - much more visible
        cr.set_source_rgba(0.95, 0.95, 0.95, 1.0)  # Almost white text
        cr.select_font_face("Sans", 0, 1)  # Bold font
        cr.set_font_size(14)  # Larger font
        text_extents = cr.text_extents(self.label_text)
        cr.move_to(center_x - text_extents.width / 2, center_y + text_extents.height / 2)
        cr.show_text(self.label_text)

class SensorMonitor(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("System Sensor Monitor")
        self.set_default_size(900, 700)
        
        # Header bar
        header = Gtk.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Sensor Monitor"))
        self.set_titlebar(header)
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda x: self.update_sensors())
        header.pack_end(refresh_btn)
        
        # Debug button to print sensor data
        debug_btn = Gtk.Button()
        debug_btn.set_icon_name("document-edit-symbolic")
        debug_btn.connect("clicked", lambda x: self.debug_sensors())
        header.pack_end(debug_btn)
        
        # Main container
        self.setup_ui()
        self.setup_css()
        
        # Start updating
        self.update_sensors()
        GLib.timeout_add_seconds(3, self.update_sensors)  # Update every 3 seconds
    
    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        # Overview section with circular progress indicators
        overview_label = Gtk.Label(label="System Overview")
        overview_label.add_css_class("title-2")
        overview_label.set_xalign(0)
        main_box.append(overview_label)
        
        overview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        overview_box.set_halign(Gtk.Align.CENTER)
        
        # CPU Temperature circular indicator
        cpu_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cpu_label = Gtk.Label(label="CPU Package")
        cpu_label.add_css_class("caption")
        self.cpu_circle = CircularProgress(100)
        cpu_container.append(self.cpu_circle)
        cpu_container.append(cpu_label)
        overview_box.append(cpu_container)
        
        # NVMe Temperature
        nvme_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        nvme_label = Gtk.Label(label="NVMe SSD")
        nvme_label.add_css_class("caption")
        self.nvme_circle = CircularProgress(100)
        nvme_container.append(self.nvme_circle)
        nvme_container.append(nvme_label)
        overview_box.append(nvme_container)
        
        # Fan Speed
        fan_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        fan_label = Gtk.Label(label="Cooling Fan")
        fan_label.add_css_class("caption")
        self.fan_circle = CircularProgress(100)
        fan_container.append(self.fan_circle)
        fan_container.append(fan_label)
        overview_box.append(fan_container)
        
        main_box.append(overview_box)
        
        # Separator
        separator = Gtk.Separator()
        main_box.append(separator)
        
        # Detailed sensors section
        sensors_label = Gtk.Label(label="Detailed Sensors")
        sensors_label.add_css_class("title-2")
        sensors_label.set_xalign(0)
        main_box.append(sensors_label)
        
        # Scrollable area for sensor cards
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        # Flow box for sensor cards
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(4)
        self.flowbox.set_min_children_per_line(2)
        self.flowbox.set_row_spacing(16)
        self.flowbox.set_column_spacing(16)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        scrolled.set_child(self.flowbox)
        main_box.append(scrolled)
        
        self.set_child(main_box)
    
    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css = """
        .sensor-card {
            padding: 18px;
            border-radius: 12px;
            background: alpha(currentColor, 0.15);
            border: 2px solid alpha(currentColor, 0.25);
            min-height: 120px;
        }
        
        .sensor-card:hover {
            background: alpha(currentColor, 0.20);
            border: 2px solid alpha(currentColor, 0.35);
        }
        
        .sensor-card .title-4 {
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .sensor-card .caption {
            opacity: 0.8;
            font-size: 0.9em;
        }
        
        .sensor-card .heading {
            font-weight: bold;
            font-size: 1.0em;
        }
        
        .success { 
            color: #26a269;
            font-weight: bold;
        }
        .warning { 
            color: #e5a50a;
            font-weight: bold;
        }
        .error { 
            color: #c01c28;
            font-weight: bold;
        }
        .accent { 
            color: #1c71d8;
            font-weight: bold;
        }
        """
        css_provider.load_from_string(css)
        
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def debug_sensors(self):
        """Print raw sensor data for debugging"""
        try:
            result = subprocess.run(['sensors', '-u'], capture_output=True, text=True)
            print("=== RAW SENSOR OUTPUT ===")
            print(result.stdout)
            print("=== END RAW OUTPUT ===")
        except Exception as e:
            print(f"Error running sensors: {e}")
    
    def parse_sensors_simple(self):
        """Simple and robust sensor parsing"""
        try:
            result = subprocess.run(['sensors', '-u'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            
            sensors = {}
            current_sensor = None
            current_adapter = ""
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('ERROR:'):
                    continue
                
                # New sensor (no indentation, no colon)
                if not line.startswith(' ') and ':' not in line:
                    current_sensor = line
                    sensors[current_sensor] = {
                        'adapter': '',
                        'temps': {},
                        'fans': {},
                        'voltages': {},
                        'other': {}
                    }
                
                # Adapter
                elif line.startswith('Adapter:'):
                    if current_sensor:
                        sensors[current_sensor]['adapter'] = line.replace('Adapter:', '').strip()
                
                # Temperature input
                elif 'temp' in line and '_input:' in line:
                    try:
                        temp_name = line.split('_input:')[0].strip()
                        temp_value = float(line.split(':')[1].strip())
                        if current_sensor:
                            sensors[current_sensor]['temps'][temp_name] = temp_value
                    except (ValueError, IndexError):
                        pass
                
                # Fan input
                elif 'fan' in line and '_input:' in line:
                    try:
                        fan_name = line.split('_input:')[0].strip()
                        fan_value = float(line.split(':')[1].strip())
                        if current_sensor:
                            sensors[current_sensor]['fans'][fan_name] = fan_value
                    except (ValueError, IndexError):
                        pass
                
                # Voltage input
                elif 'in' in line and '_input:' in line:
                    try:
                        volt_name = line.split('_input:')[0].strip()
                        volt_value = float(line.split(':')[1].strip())
                        if current_sensor:
                            sensors[current_sensor]['voltages'][volt_name] = volt_value
                    except (ValueError, IndexError):
                        pass
            
            return sensors
        except Exception as e:
            print(f"Error parsing sensors: {e}")
            return {}
    
    def update_sensors(self):
        sensors_data = self.parse_sensors_simple()
        
        # Clear existing cards
        child = self.flowbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.flowbox.remove(child)
            child = next_child
        
        # Track values for overview circles
        max_cpu_temp = 0
        max_nvme_temp = 0
        max_fan_speed = 0
        
        # Create cards for each sensor
        for sensor_name, data in sensors_data.items():
            if not data['temps'] and not data['fans'] and not data['voltages']:
                continue
            
            # Determine icon and display name
            display_name = sensor_name
            icon = "temperature-symbolic"
            
            if 'coretemp' in sensor_name:
                display_name = "CPU Cores"
                icon = "cpu-symbolic"
            elif 'nvme' in sensor_name:
                display_name = f"NVMe SSD"
                icon = "drive-harddisk-symbolic"
            elif 'hp-isa' in sensor_name or 'fan' in sensor_name:
                display_name = "System Fans"
                icon = "weather-windy-symbolic"
            elif 'iwlwifi' in sensor_name:
                display_name = "WiFi Module"
                icon = "network-wireless-symbolic"
            elif 'BAT' in sensor_name:
                display_name = "Battery"
                icon = "battery-symbolic"
            elif 'acpitz' in sensor_name:
                display_name = "ACPI Thermal"
                icon = "temperature-symbolic"
            
            # Create card
            card = SensorCard(display_name, data['adapter'], icon)
            
            # Add temperature values
            for temp_name, temp_value in data['temps'].items():
                if 'coretemp' in sensor_name and temp_value > max_cpu_temp:
                    max_cpu_temp = temp_value
                elif 'nvme' in sensor_name and temp_value > max_nvme_temp:
                    max_nvme_temp = temp_value
                
                friendly_name = temp_name.replace('temp', 'Sensor ').replace('1', 'Main')
                if 'Package' in temp_name:
                    friendly_name = "Package"
                elif 'Core' in temp_name:
                    friendly_name = temp_name
                elif 'Composite' in temp_name:
                    friendly_name = "Composite"
                
                card.add_value(friendly_name, temp_value, "°C")
            
            # Add fan values
            for fan_name, fan_value in data['fans'].items():
                if fan_value > max_fan_speed:
                    max_fan_speed = fan_value
                
                friendly_name = fan_name.replace('fan', 'Fan ').capitalize()
                card.add_value(friendly_name, fan_value, " RPM")
            
            # Add voltage values
            for volt_name, volt_value in data['voltages'].items():
                friendly_name = volt_name.replace('in', 'Input ').replace('0', '1')
                card.add_value(friendly_name, volt_value, "V")
            
            self.flowbox.append(card)
        
        # Update circular indicators
        if max_cpu_temp > 0:
            self.cpu_circle.set_value(max_cpu_temp, 100, f"{max_cpu_temp:.1f}°C")
        else:
            self.cpu_circle.set_value(0, 100, "N/A")
        
        if max_nvme_temp > 0:
            self.nvme_circle.set_value(max_nvme_temp, 85, f"{max_nvme_temp:.1f}°C")
        else:
            self.nvme_circle.set_value(0, 85, "N/A")
        
        if max_fan_speed > 0:
            self.fan_circle.set_value(max_fan_speed, 3000, f"{int(max_fan_speed)}", (0.2, 0.7, 0.9))
        else:
            self.fan_circle.set_value(0, 3000, "N/A", (0.5, 0.5, 0.5))
        
        return True  # Keep the timeout running

class SensorApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)
    
    def on_activate(self, app):
        self.win = SensorMonitor(application=app)
        self.win.present()

def main():
    app = SensorApp(application_id="com.example.sensormonitor")
    return app.run(None)

if __name__ == '__main__':
    main()
