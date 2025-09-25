"""
Test script for popup alerts.
"""
import os
import sys
import time
import subprocess
import tempfile

def create_popup_windows(title, message, level):
    """Create a Windows popup alert directly without importing the module."""
    print(f"Creating {level} popup: {title} - {message}")
    
    # Set the color based on alert level
    if level == "critical":
        bg_color = "LightPink"
        sound = "Hand"
        icon = "Error"
    elif level == "warning":
        bg_color = "LightYellow"
        sound = "Exclamation"
        icon = "Warning"
    else:  # normal
        bg_color = "LightBlue"
        sound = "Asterisk"
        icon = "Information"
    
    # Create the PowerShell script
    script = f"""
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    
    # Play sound
    [System.Media.SystemSounds]::{sound}.Play()
    
    # Create form
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'FocusGuard Alert'
    $form.Size = New-Object System.Drawing.Size(400, 200)
    $form.TopMost = $true
    $form.StartPosition = 'CenterScreen'
    $form.BackColor = [System.Drawing.Color]::{bg_color}
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    
    # Create title label
    $titleLabel = New-Object System.Windows.Forms.Label
    $titleLabel.Text = '{title}'
    $titleLabel.Font = New-Object System.Drawing.Font('Arial', 12, [System.Drawing.FontStyle]::Bold)
    $titleLabel.Location = New-Object System.Drawing.Point(20, 20)
    $titleLabel.Size = New-Object System.Drawing.Size(360, 25)
    $form.Controls.Add($titleLabel)
    
    # Create message label
    $messageLabel = New-Object System.Windows.Forms.Label
    $messageLabel.Text = '{message}'
    $messageLabel.Font = New-Object System.Drawing.Font('Arial', 10)
    $messageLabel.Location = New-Object System.Drawing.Point(20, 50)
    $messageLabel.Size = New-Object System.Drawing.Size(360, 100)
    $messageLabel.AutoSize = $true
    $form.Controls.Add($messageLabel)
    
    # Auto-close timer
    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 5000
    $timer.Add_Tick({{$form.Close(); $timer.Stop()}})
    $timer.Start()
    
    # Show form
    $form.ShowDialog() | Out-Null
    """
    
    # Save script to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ps1', mode='w', encoding='utf-8') as temp:
        temp_path = temp.name
        temp.write(script)
    
    # Run the PowerShell script
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_path]
    subprocess.Popen(cmd)

def test_popup():
    """Test the popup alert system with different alert levels."""
    
    # Test normal alert (blue)
    print("Testing normal alert (blue)...")
    create_popup_windows('Normal Alert', 'This is a normal alert with blue background', 'normal')
    time.sleep(6)  # Wait for the popup to close
    
    # Test warning alert (orange/yellow)
    print("Testing warning alert (yellow)...")
    create_popup_windows('Warning Alert', 'This is a warning alert with yellow background', 'warning')
    time.sleep(6)  # Wait for the popup to close
    
    # Test critical alert (red)
    print("Testing critical alert (red)...")
    create_popup_windows('Critical Alert', 'This is a critical alert with red background', 'critical')
    time.sleep(6)  # Wait for the popup to close
    
    print("All tests completed!")

if __name__ == "__main__":
    test_popup()
