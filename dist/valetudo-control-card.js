import { LitElement, html, css } from 'https://unpkg.com/lit?module';

class ValetudoControlCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
      _velocity: { type: Number },
      _angle: { type: Number },
      _isConnected: { type: Boolean },
      _isManualControlEnabled: { type: Boolean },
      _isTogglingManualControl: { type: Boolean },
      _lastWaterUsagePreset: { type: String },
    };
  }

  static get styles() {
    return css`
      :host {
        display: block;
      }
      
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        font-size: 16px;
        font-weight: 500;
      }
      
      .battery-level {
        font-size: 14px;
        font-weight: normal;
        color: var(--secondary-text-color);
      }
      
      .status-top {
        display: flex;
        justify-content: space-between;
        padding: 0 16px;
        margin-bottom: 8px;
      }
      
      .status-item-top {
        text-align: center;
      }
      
      .status-value-top {
        font-size: 16px;
        font-weight: bold;
      }
      
      .status-label-top {
        font-size: 10px;
        color: var(--secondary-text-color);
      }
      
      .card-content {
        padding: 0 16px 16px;
      }
      
      .joystick-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-bottom: 16px;
      }
      
      .joystick-area {
        position: relative;
        width: 200px;
        height: 200px;
        border-radius: 50%;
        background-color: var(--secondary-background-color);
        margin-bottom: 16px;
        touch-action: none;
        user-select: none;
        -webkit-user-select: none;
        -webkit-touch-callout: none;
      }
      
      .joystick-handle {
        position: absolute;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background-color: var(--primary-color);
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        cursor: move;
        pointer-events: none;
        touch-action: none;
        user-select: none;
        -webkit-user-select: none;
        -webkit-touch-callout: none;
        transition: transform 0.1s ease;
      }
      
      .joystick-handle:active {
        transform: translate(-50%, -50%) scale(1.1);
      }
      
      .controls {
        display: flex;
        justify-content: space-between;
        width: 100%;
        margin-bottom: 16px;
      }
      
      .control-button {
        flex: 1;
        margin: 0 4px;
        padding: 8px;
        text-align: center;
        background-color: var(--secondary-background-color);
        border-radius: 4px;
        cursor: pointer;
        user-select: none;
        touch-action: manipulation;
        -webkit-tap-highlight-color: transparent;
        transition: background-color 0.2s ease;
      }
      
      .control-button:active {
        background-color: var(--primary-color);
        color: var(--text-primary-color);
      }
      
      .control-button.active {
        background-color: var(--primary-color);
        color: var(--text-primary-color);
      }
      
      .control-button.loading {
        opacity: 0.7;
        pointer-events: none;
      }
      
      .spinner {
        display: inline-block;
        width: 12px;
        height: 12px;
        border: 2px solid transparent;
        border-top: 2px solid currentColor;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-right: 8px;
        vertical-align: middle;
      }
      
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
      
      .status {
        display: flex;
        justify-content: space-between;
        width: 100%;
        margin-top: 16px;
      }
      
      .status-item {
        text-align: center;
      }
      
      .status-value {
        font-size: 18px;
        font-weight: bold;
      }
      
      .status-label {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
    `;
  }

  constructor() {
    super();
    this._velocity = 0;
    this._angle = 0;
    this._isConnected = false;
    this._isManualControlEnabled = false;
    this._isManualControlStateKnown = false;
    this._isTogglingManualControl = false;
    this._lastWaterUsagePreset = null;
    this.speed = 1.0; // Always use max speed
    this.deadzone = 0.15;
    this.angleEpsilon = 3.0;  // Minimum angle change to trigger command (align with backend)
    this.velocityEpsilon = 0.02;  // Minimum velocity change to trigger command (align with backend)
    this._commandInterval = null;
    this._commandIntervalMs = 250; // Match Valetudo's implementation
    this._lastSent = { angle: null, velocity: null };
    this._lastSendTime = 0;
    this._pollingInterval = null;
    this._pollingIntervalMs = 5000; // Poll every 5 seconds instead of 1 second
    this._debugMode = false; // Debug mode flag
    
    // Bind event handlers to preserve 'this' context
    this._boundHandleJoystickMove = this._handleJoystickMove.bind(this);
    this._boundHandleJoystickEnd = this._handleJoystickEnd.bind(this);
  }
  
  // Debug logging helper
  _debug(...args) {
    if (this._debugMode) {
      console.log(...args);
    }
  }

  firstUpdated() {
    this._debug('ValetudoControlCard first updated');
    // Ensure the joystick handle is properly positioned when the component is first rendered
    setTimeout(() => {
      this._resetJoystick(false); // Don't send stop command when initializing
    }, 100);
  }

  updated(changedProperties) {
    // Handle manual control state changes
    if (changedProperties.has('_isManualControlEnabled')) {
      // If manual control is disabled and the joystick is being dragged, stop it
      if (!this._isManualControlEnabled && this._isDragging) {
        this._isDragging = false;
        
        // Stop continuous command sending
        if (this._commandInterval) {
          clearInterval(this._commandInterval);
          this._commandInterval = null;
        }
        
        // Reset joystick position
        this._resetJoystick();
      }
    }
    
    // Only reset joystick if we're not currently dragging
    if (this._isDragging) {
      return;
    }
    
    let shouldResetJoystick = false;
    
    // If manual control is disabled, ensure the joystick is reset
    if (changedProperties.has('_isManualControlEnabled') && !this._isManualControlEnabled) {
      shouldResetJoystick = true;
    }
    // If manual control is enabled, ensure the joystick is properly positioned
    if (changedProperties.has('_isManualControlEnabled') && this._isManualControlEnabled) {
      shouldResetJoystick = true;
    }
    // If velocity or angle changes, ensure the joystick is properly positioned
    if (changedProperties.has('_velocity') || changedProperties.has('_angle')) {
      shouldResetJoystick = true;
    }
    // If config object changes, ensure the joystick is properly positioned
    if (changedProperties.has('config')) {
      shouldResetJoystick = true;
    }
    // If isConnected property changes, ensure the joystick is properly positioned
    if (changedProperties.has('_isConnected')) {
      shouldResetJoystick = true;
    }
    
    if (shouldResetJoystick) {
      this._resetJoystick();
    }
  }

  setConfig(config) {
    this._debug('ValetudoControlCard setConfig called with:', config);
    if (!config.entity) {
      throw new Error('You need to define an entity');
    }
    this.config = config;
    // Check if debug mode is enabled in the config
    this._debugMode = config.debug_mode || false;
  }

  connectedCallback() {
    super.connectedCallback();
    this._debug('ValetudoControlCard connected');
    this._isConnected = true;
    // Ensure the joystick handle is properly positioned when the component is connected
    setTimeout(() => {
      this._resetJoystick(false); // Don't send stop command when initializing
    }, 100);
    
    // Initialize manual control state first
    this._initializeManualControlState();
    
    // Then start polling for manual control state
    this._startPolling();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._debug('ValetudoControlCard disconnected');
    this._isConnected = false;
    
    // Stop continuous command sending
    if (this._commandInterval) {
      this._debug('Clearing command interval');
      clearInterval(this._commandInterval);
      this._commandInterval = null;
    }
    
    // Stop polling
    if (this._pollingInterval) {
      this._debug('Clearing polling interval');
      clearInterval(this._pollingInterval);
      this._pollingInterval = null;
    }
    
    // Reset joystick position
    this._resetJoystick();
    
    // Send stop command
    this._sendStopCommand();
  }

  _handleJoystickStart(e) {
    e.preventDefault();
    e.stopPropagation();
    
    // Only handle joystick if manual control is enabled
    if (!this._isManualControlEnabled) {
      return;
    }
    
    this._isDragging = true;
    this._joystickArea = this.renderRoot.querySelector('.joystick-area');
    this._joystickHandle = this.renderRoot.querySelector('.joystick-handle');
    
    // Add event listeners to the document to capture events outside the joystick area
    document.addEventListener('mousemove', this._boundHandleJoystickMove, { passive: false });
    document.addEventListener('touchmove', this._boundHandleJoystickMove, { passive: false });
    document.addEventListener('mouseup', this._boundHandleJoystickEnd);
    document.addEventListener('touchend', this._boundHandleJoystickEnd);
    
    this._updateJoystickPosition(e);
    
    // Send initial command immediately
    this._sendCommand(this._velocity, this._angle);
    
    // Start continuous command sending
    if (this._commandInterval) {
      clearInterval(this._commandInterval);
    }
    // Add a small delay before starting continuous commands to ensure initial position is calculated
    setTimeout(() => {
      this._commandInterval = setInterval(() => {
        this._sendCommand(this._velocity, this._angle);
      }, this._commandIntervalMs);
    }, 50);
  }

  _handleJoystickMove(e) {
    if (!this._isDragging) {
      return;
    }
    e.preventDefault();
    e.stopPropagation();
    this._updateJoystickPosition(e);
  }

  _handleJoystickEnd(e) {
    if (!this._isDragging) {
      return;
    }
    e.preventDefault();
    e.stopPropagation();
    this._isDragging = false;
    
    // Remove event listeners from the document
    document.removeEventListener('mousemove', this._boundHandleJoystickMove);
    document.removeEventListener('touchmove', this._boundHandleJoystickMove);
    document.removeEventListener('mouseup', this._boundHandleJoystickEnd);
    document.removeEventListener('touchend', this._boundHandleJoystickEnd);
    
    // Stop continuous command sending
    if (this._commandInterval) {
      clearInterval(this._commandInterval);
      this._commandInterval = null;
    }
    
    // Reset joystick position immediately
    this._resetJoystick();
  }

  _updateJoystickPosition(e) {
    if (!this._joystickArea || !this._joystickHandle) return;
    
    const rect = this._joystickArea.getBoundingClientRect();
    let clientX, clientY;
    
    if (e.type.includes('touch')) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }
    
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    
    // Calculate delta from center
    const deltaX = x - centerX;
    const deltaY = y - centerY;
    
    // Calculate distance from center
    const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    const maxDistance = centerX; // Radius of the joystick area
    
    // Constrain position to stay within the circle
    const constrainedDistance = Math.min(distance, maxDistance);
    const angle = Math.atan2(deltaY, deltaX);
    
    // Calculate constrained position
    const constrainedX = centerX + Math.cos(angle) * constrainedDistance;
    const constrainedY = centerY + Math.sin(angle) * constrainedDistance;
    
    // Position the joystick handle
    this._joystickHandle.style.left = `${constrainedX}px`;
    this._joystickHandle.style.top = `${constrainedY}px`;
    
    // Calculate normalized values (-1 to 1)
    // Invert Y axis to match robot coordinate system (positive Y = forward)
    const normalizedX = (constrainedX - centerX) / centerX;
    const normalizedY = -(constrainedY - centerY) / centerY;  // Inverted Y axis
    
    // Apply deadzone
    const absX = Math.abs(normalizedX);
    const absY = Math.abs(normalizedY);
    
    if (absX < this.deadzone && absY < this.deadzone) {
      this._velocity = 0;
      this._angle = 0;
    } else {
      // Calculate movement using the same logic as the backend
      this._calculateMovement(normalizedX, normalizedY);
    }
  }

  _calculateMovement(xAxis, yAxis) {
    const absX = Math.abs(xAxis);
    const absY = Math.abs(yAxis);
    const maxSpeed = this.speed; // Always use max speed
    
    // Deadzone - No movement
    if (absX < this.deadzone && absY < this.deadzone) {
      this._velocity = 0.0;
      this._angle = 0.0;
      return;
    }
    
    // Mostly vertical movement
    if (absY > this.deadzone && absX < (this.deadzone * 1.5)) {
      const velocity = this._normalizeAxisValue(absY) * maxSpeed;
      this._velocity = yAxis > 0 ? velocity : -velocity;
      this._velocity = Math.max(-1.0, Math.min(1.0, this._velocity));
      this._angle = 0.0;
      return;
    }
    
    // Mostly horizontal movement - pure rotation
    if (absX > this.deadzone && absY < (this.deadzone * 1.5)) {
      this._velocity = 0.0;
      this._angle = xAxis > 0 ? 90 : -90;
      return;
    }
    
    // Combined movement - both velocity and angle
    const correctedX = yAxis < 0 ? -xAxis : xAxis;
    this._angle = (Math.atan2(correctedX, yAxis) * 180) / Math.PI;
    
    const magnitude = Math.sqrt(xAxis * xAxis + yAxis * yAxis);
    const velocity = this._normalizeAxisValue(magnitude) * maxSpeed;
    this._velocity = yAxis > 0 ? velocity : -velocity;
    this._velocity = Math.max(-1.0, Math.min(1.0, this._velocity));
  }

  _normalizeAxisValue(value) {
    const normalized = Math.max(0.0, value - this.deadzone) / (1 - this.deadzone);
    return normalized;
  }
  
  async _getWaterUsagePreset() {
    if (!this.hass) {
      this._debug('Not getting water usage preset, hass not available');
      return;
    }
    
    try {
      this._debug('Getting water usage preset');
      // Call the backend service to get the water usage preset
      // Since we can't directly get the response, we'll use a different approach
      // For now, we'll return a default value
      return 'off';
    } catch (error) {
      console.error('Error getting water usage preset:', error);
      return null;
    }
  }
  
  async _setWaterUsagePreset(preset) {
    if (!this.hass) {
      this._debug('Not setting water usage preset, hass not available');
      return;
    }
    
    try {
      this._debug('Setting water usage preset to:', preset);
      // Call the backend service to set the water usage preset
      await this.hass.callService('valetudo_control', 'set_water_usage_preset', {
        preset: preset
      });
    } catch (error) {
      console.error('Error setting water usage preset:', error);
    }
  }

  _cycleSpeed() {
    this._speedIndex = (this._speedIndex + 1) % this.speedLevels.length;
    this.requestUpdate();
  }

  async _toggleManualControl() {
    if (!this.hass) {
      this._debug('Not toggling manual control, hass not available');
      return;
    }
    
    // Set toggling state to show loading indicator
    this._isTogglingManualControl = true;
    this.requestUpdate();
    
    // Toggle the manual control state on the robot
    try {
      const desiredState = !this._isManualControlEnabled;
      this._debug('Toggling manual control state to:', desiredState);
      
      // If we're enabling manual control, disable mopping and save the current state
      if (desiredState) {
        // Get the current water usage preset before disabling it
        this._lastWaterUsagePreset = await this._getWaterUsagePreset();
        await this._setWaterUsagePreset('off');
      }
      
      await this.hass.callService('valetudo_control', 'set_manual_control_state', {
        enable: desiredState
      });
      
      // If we're disabling manual control, restore the previous water usage preset
      if (!desiredState && this._lastWaterUsagePreset) {
        await this._setWaterUsagePreset(this._lastWaterUsagePreset);
      }
      
      // Don't update local state immediately, let the polling mechanism handle it
      // The state will be updated by the polling mechanism
      this._debug('Manual control state toggle requested, waiting for state update from polling');
      
      // If we're disabling manual control and the joystick is being dragged, stop it
      // We'll handle this when the state is actually updated by the polling mechanism
    } catch (error) {
      console.error('Error toggling manual control state:', error);
    } finally {
      // Don't clear toggling state here, let the polling mechanism handle it
      // The toggling state will be cleared when the manual control state is updated
      this.requestUpdate();
    }
  }

  _sendCommand(velocity, angle) {
    if (!this.hass) {
      this._debug('Not sending command, hass not available');
      return;
    }
    
    // Only send commands if manual control is enabled
    if (!this._isManualControlEnabled) {
      this._debug('Not sending command, manual control is not enabled');
      return;
    }
    
    // Ensure values are proper numbers
    let numVelocity = Number(velocity);
    let numAngle = Number(angle);
    
    // Validate and clamp values
    if (isNaN(numVelocity) || isNaN(numAngle)) {
      console.error('Invalid velocity or angle values:', velocity, angle);
      return;
    }
    
    // Clamp velocity to [-1, 1]
    numVelocity = Math.max(-1.0, Math.min(1.0, numVelocity));
    
    // Round values to appropriate precision
    numVelocity = Math.round(numVelocity * 1000) / 1000;  // 3 decimal places
    numAngle = Math.round(numAngle * 10) / 10;  // 1 decimal place
    
    // Filter out near-zero velocity commands to prevent stuttering
    // If velocity is very small, treat it as zero
    if (Math.abs(numVelocity) < this.velocityEpsilon) {
      numVelocity = 0;
    }
    
    // Get current time in milliseconds
    const currentTime = new Date().getTime();
    const timeSinceLastSend = currentTime - this._lastSendTime;
    
    // Check if values have changed significantly
    const angleChanged = this._lastSent.angle === null || Math.abs(numAngle - this._lastSent.angle) > this.angleEpsilon;
    const velocityChanged = this._lastSent.velocity === null || Math.abs(numVelocity - this._lastSent.velocity) > this.velocityEpsilon;
    
    // Send command if enough time has passed or if values have changed significantly
    const shouldSend = (
      this._lastSent.angle === null ||  // First command always sends
      timeSinceLastSend >= this._commandIntervalMs ||  // Time interval has passed
      angleChanged ||  // Angle has changed significantly
      velocityChanged  // Velocity has changed significantly
    );
    
    // Additional check to prevent sending unnecessary zero commands
    // Only send zero velocity command if we're not already sending zero velocity
    // Exception: Allow continuous rotation commands (zero velocity with non-zero angle)
    if (numVelocity === 0 && this._lastSent.velocity === 0 && !angleChanged && numAngle === 0) {
      this._debug('Not sending command, already sending zero velocity with no angle change');
      return;
    }
    
    if (!shouldSend) {
      // No need to send command
      this._debug('Not sending command, no significant change or time interval not reached');
      return;
    }
    
    this._debug('Sending command with velocity:', numVelocity, 'angle:', numAngle);
    try {
      // Create service data with explicitly typed values
      const serviceData = {
        velocity: numVelocity,
        angle: numAngle
      };
      this.hass.callService('valetudo_control', 'send_command', serviceData);
    } catch (error) {
      console.error('Error calling send_command service:', error);
      // Don't update last sent values if the call failed
      return;
    }
    
    // Update last sent values and time
    this._lastSent = { angle: numAngle, velocity: numVelocity };
    this._lastSendTime = currentTime;
  }

  _resetJoystick(sendStopCommand = true) {
    // Reset joystick position
    if (this._joystickHandle) {
      this._joystickHandle.style.transform = 'translate(-50%, -50%) scale(1)';
      this._joystickHandle.style.left = '50%';
      this._joystickHandle.style.top = '50%';
    }
    
    // Reset velocity and angle
    // Only trigger property updates if we're not currently dragging
    if (!this._isDragging) {
      this._velocity = 0;
      this._angle = 0;
    }
    
    // Send stop command only if requested
    if (sendStopCommand) {
      this._sendCommand(0, 0);
    }
  }

  _sendStopCommand() {
    this._sendCommand(0, 0);
  }

  _initializeManualControlState() {
    if (!this.hass || !this.config || !this.config.entity) return;
    
    // Find the manual control switch entity by searching for entities with "manual_control" in their name or ID
    let switchEntity = null;
    for (const [entityId, entity] of Object.entries(this.hass.states)) {
      if (entityId.startsWith('switch.')) {
        // Check if this is the manual control switch
        if (entityId.includes('_manual_control') ||
            entityId.includes('manual_control_') ||
            (entity.attributes?.friendly_name && entity.attributes.friendly_name.includes('Manual Control'))) {
          switchEntity = entity;
          break;
        }
      }
    }
    
    if (switchEntity) {
      const manualControlState = switchEntity.state === 'on';
      // Only update if the state has actually changed
      if (this._isManualControlEnabled !== manualControlState) {
        this._debug('Updating manual control state to:', manualControlState);
        this._isManualControlEnabled = manualControlState;
        this._isManualControlStateKnown = true;
        this.requestUpdate();
      }
    }
    
  }

  _dock() {
    if (!this.hass) {
      this._debug('Not docking, hass not available');
      return;
    }
    
    this._debug('Docking robot');
    try {
      this.hass.callService('valetudo_control', 'dock', {});
    } catch (error) {
      console.error('Error calling dock service:', error);
    }
  }

  _playSound() {
    if (!this.hass) {
      this._debug('Not playing sound, hass not available');
      return;
    }
    
    this._debug('Playing sound');
    try {
      this.hass.callService('valetudo_control', 'play_sound', {});
    } catch (error) {
      console.error('Error calling play_sound service:', error);
    }
  }

  _startPolling() {
    // Clear any existing polling interval
    if (this._pollingInterval) {
      clearInterval(this._pollingInterval);
    }
    
    // Start polling for manual control state every 5 seconds
    this._pollingInterval = setInterval(() => {
      if (!this.hass || !this.config || !this.config.entity) return;
      
      // Try to find the manual control switch entity
      this._findAndSetManualControlState();
    }, 5000); // Poll every 5 seconds instead of 1 second
  }

  _findAndSetManualControlState() {
    if (!this.hass || !this.config || !this.config.entity) return;
    
    // Find the manual control switch entity by searching for entities with "manual_control" in their name or ID
    let switchEntity = null;
    for (const [entityId, entity] of Object.entries(this.hass.states)) {
      if (entityId.startsWith('switch.')) {
        // Check if this is the manual control switch
        if (entityId.includes('_manual_control') ||
            entityId.includes('manual_control_') ||
            (entity.attributes?.friendly_name && entity.attributes.friendly_name.includes('Manual Control'))) {
          switchEntity = entity;
          break;
        }
      }
    }
    
    if (switchEntity) {
      const manualControlState = switchEntity.state === 'on';
      // Only update if the state has actually changed
      if (this._isManualControlEnabled !== manualControlState) {
        this._debug('Updating manual control state to:', manualControlState);
        this._isManualControlEnabled = manualControlState;
        this._isManualControlStateKnown = true;
        // Clear toggling state when manual control state is updated
        this._isTogglingManualControl = false;
        this.requestUpdate();
      } else if (this._isTogglingManualControl) {
        // If the state hasn't changed but we're still toggling, clear the toggling state
        this._isTogglingManualControl = false;
        this.requestUpdate();
      }
    } else {
      // Try to initialize it again
      // This might happen if the entity is created after the card is loaded
      this._initializeManualControlState();
    }
  }

  render() {
    const entityId = this.config.entity;
    const stateObj = this.hass.states[entityId];
    
    return html`
      <ha-card>
        <div class="card-header">
          <div class="name">Valetudo Control</div>
          ${stateObj && stateObj.attributes && stateObj.attributes.battery_level !== undefined
            ? html`<div class="battery-level">${stateObj.attributes.battery_level}%</div>`
            : ''}
        </div>
        <div class="status-top">
          <div class="status-item-top">
            <div class="status-value-top">${this._velocity.toFixed(2)}</div>
            <div class="status-label-top">Velocity</div>
          </div>
          <div class="status-item-top">
            <div class="status-value-top">${this._angle.toFixed(1)}°</div>
            <div class="status-label-top">Angle</div>
          </div>
        </div>
        <div class="card-content">
          <div class="joystick-container">
            <div class="joystick-area"
              @mousedown="${this._handleJoystickStart}"
              @touchstart="${this._handleJoystickStart}"
              @mousemove="${this._handleJoystickMove}"
              @touchmove="${this._handleJoystickMove}"
              @mouseup="${this._handleJoystickEnd}"
              @touchend="${this._handleJoystickEnd}">
              <div class="joystick-handle"></div>
            </div>
          </div>
          
          <div class="controls">
            <div class="control-button ${this._isManualControlEnabled ? 'active' : ''} ${this._isTogglingManualControl ? 'loading' : ''}" @click="${this._toggleManualControl}">
              ${this._isTogglingManualControl ? html`<span class="spinner"></span> Toggling...` : (this._isManualControlEnabled ? 'Disable' : 'Enable')} Control
            </div>
            <div class="control-button" @click="${this._playSound}">
              Locate
            </div>
            <div class="control-button" @click="${this._dock}">
              Dock
            </div>
          </div>
        </div>
      </ha-card>
    `;
  }

  static getConfigElement() {
    return document.createElement('valetudo-control-card-editor');
  }

  static getStubConfig() {
    return {
      entity: 'sensor.valetudo_robot_battery'
    };
  }
}

class ValetudoControlCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      _config: { type: Object },
    };
  }

  setConfig(config) {
    this._config = config;
  }

  configChanged(newConfig) {
    const event = new Event('config-changed', {
      bubbles: true,
      composed: true,
    });
    event.detail = { config: newConfig };
    this.dispatchEvent(event);
  }

  render() {
    if (!this.hass || !this._config) {
      return html``;
    }

    return html`
      <div class="card-config">
        <ha-entity-picker
          .hass="${this.hass}"
          .value="${this._config.entity}"
          .configValue="${'entity'}"
          @value-changed="${this._valueChanged}"
          allow-custom-entity
        ></ha-entity-picker>
      </div>
    `;
  }

  _valueChanged(ev) {
    if (!this._config || !this.hass) {
      return;
    }
    const target = ev.target;
    if (this[`_${target.configValue}`] === target.value) {
      return;
    }
    if (target.configValue) {
      // Handle checkbox values
      let value = target.value;
      if (target.type === 'checkbox') {
        value = target.checked;
      } else if (target.tagName === 'HA-SWITCH') {
        value = target.checked;
      }
      
      this._config = {
        ...this._config,
        [target.configValue]: value,
      };
    }
    this.configChanged(this._config);
  }
}

customElements.define('valetudo-control-card', ValetudoControlCard);
customElements.define('valetudo-control-card-editor', ValetudoControlCardEditor);
