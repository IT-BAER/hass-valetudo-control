# Valetudo Control Integration for Home Assistant

A Home Assistant integration that provides joystick-like control for Valetudo-powered robot vacuums using the new high-resolution API endpoint introduced in May 2025.

## 🌟 Features

- 🕹️ **Joystick Control**: Full joystick-like control for your robot vacuum
- 🚀 **High-Resolution API**: Utilizes the new high-resolution manual control capability
- 🔐 **Basic Auth Support**: Connect to your Valetudo robot with username/password authentication
- 🎛️ **Frontend Card**: Custom Lovelace card with interactive joystick control (separate installation)
- 🔄 **Manual Control Toggle**: Enable/disable manual control on the robot
- 🔋 **Battery Monitoring**: Monitor your robot's battery level
- ⚡ **Quick Actions**: Dock robot and play sound

## 📋 Requirements

- Home Assistant 2024.1.0 or later
- A robot vacuum running Valetudo > 2025.05.0 with `HighResolutionManualControlCapability`
- Basic authentication configured on your Valetudo instance (optional)

## 💻 Installation

### 🧩 HACS Custom Repository Installation (Recommended)

1. Install [HACS](https://hacs.xyz/docs/installation/prerequisites)
2. Go to HACS > Integrations > ⋮ (three dots) > Custom repositories
3. Add this repository URL (`https://github.com/Hypfer/hass-valetudo-control`) with category "Integration"
4. Go back to HACS > Integrations > Explore & Add Repositories
5. Search for "Valetudo Control" and install the integration
6. Restart Home Assistant
7. Add the integration via Settings > Devices & Services > + Add Integration
8. To install the card, go to HACS > Frontend > ⋮ (three dots) > Custom repositories
9. Add this repository URL (`https://github.com/Hypfer/hass-valetudo-control`) with category "Lovelace"
10. Go back to HACS > Frontend > Explore & Add Repositories
11. Search for "Valetudo Control" and install the card
12. Add the card to your Lovelace dashboard

### 🔧 Manual Installation

1. Copy the `custom_components/valetudo_control` folder to your `custom_components` directory
2. Copy the `dist/valetudo-control-card.js` file to your `www` directory
3. Restart Home Assistant
4. Add the integration via Settings > Devices & Services > + Add Integration

## ⚙️ Configuration

### 🤖 Integration Setup

1. Go to Settings > Devices & Services > + Add Integration
2. Search for "Valetudo Control"
3. Enter your robot's IP address and optional username/password
4. Click Submit

### 🎴 Frontend Card Setup

After installing the card through HACS, add the following to your Lovelace configuration:

```yaml
- type: custom:valetudo-control-card
  entity: sensor.your_robot_battery
```

Replace `sensor.your_robot_battery` with your robot's battery sensor entity ID.

## 🎮 Usage

### 🕹️ Frontend Card

The custom Lovelace card provides:

- **Joystick Area**: Drag the joystick to control your robot
- **Enable/Disable Control**: Toggle manual control on/off
- **Sound Button**: Play a test sound on the robot
- **Dock Button**: Send the robot back to its dock
- **Status Display**: Shows current velocity and angle

### 🛠️ Services

The integration provides the following services:

- `valetudo_control.send_command`: Send a movement command
  - `velocity`: Velocity (-1.0 to 1.0)
  - `angle`: Angle in degrees (-180 to 180)
- `valetudo_control.dock`: Send the robot to its dock
- `valetudo_control.play_sound`: Play a test sound
- `valetudo_control.get_manual_control_state`: Get manual control state
- `valetudo_control.set_manual_control_state`: Enable/disable manual control
  - `enable`: Boolean to enable or disable

### 🎛️ Manual Control

The integration uses the new high-resolution manual control API:

1. **Enable Manual Control**: Click the "Enable Control" button on the card or use the service
2. **Control Robot**: Use the joystick to move the robot
3. **Disable Manual Control**: Click the "Disable Control" button or use the service

## 🆘 Troubleshooting

### 🔌 Connection Issues

- Ensure your robot is powered on and connected to the network
- Verify the IP address is correct
- Check that Valetudo is running and accessible
- If using authentication, verify username/password

### 🎮 Manual Control Not Working

- Ensure your Valetudo version supports `HighResolutionManualControlCapability` (requires > 2025.05.0)
- Check that manual control is enabled in the Valetudo web interface
- Verify the robot is not currently cleaning

### 🖥️ Card Not Loading

- Ensure the card is properly installed through HACS
- Clear your browser cache
- Check the browser console for errors

## 📡 API Reference

### 🎮 High-Resolution Manual Control

The integration uses the following API endpoints:

- `GET /api/v2/robot/capabilities/HighResolutionManualControlCapability` - Get manual control state
- `PUT /api/v2/robot/capabilities/HighResolutionManualControlCapability` - Enable/disable manual control
- `PUT /api/v2/robot/capabilities/HighResolutionManualControlCapability` - Send movement commands

### 📤 Movement Commands

Movement commands are sent with the following payload:

```json
{
  "action": "move",
  "vector": {
    "velocity": 0.5,
    "angle": 45
  }
}
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

- Thanks to the [Valetudo](https://github.com/Hypfer/Valetudo) team for the high-resolution API
