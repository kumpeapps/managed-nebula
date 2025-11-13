# Mobile Enrollment Guide

This guide explains how to enroll mobile devices (iOS and Android) into your Managed Nebula mesh network using one-time enrollment codes.

## Overview

Mobile enrollment provides a secure, user-friendly way to onboard mobile devices without manually configuring certificates and settings. Users can simply scan a QR code or enter an enrollment URL, and their device will automatically receive its configuration and connect to the network.

## Features

- **One-Time Codes**: Each enrollment code can only be used once for security
- **QR Code Scanning**: Users can scan QR codes with the Mobile Nebula app
- **Time-Limited**: Codes expire after a configurable period (1 hour to 7 days)
- **Device Tracking**: Track which devices have enrolled and their platform information
- **Permission-Based**: Only authorized users can generate codes for clients they manage

## Prerequisites

- Managed Nebula server with mobile enrollment feature enabled
- Mobile Nebula app installed on the device ([iOS](https://apps.apple.com/app/mobile-nebula/id1509587936) or [Android](https://play.google.com/store/apps/details?id=net.defined.mobile_nebula))
- A client (node) configured in Managed Nebula with an IP assignment

## For Administrators: Generating Enrollment Codes

### Step 1: Navigate to Mobile Enrollment

1. Log into the Managed Nebula web interface
2. Click on **"Mobile Enrollment"** in the navigation bar

### Step 2: Generate an Enrollment Code

1. Click the **"Generate Enrollment Code"** button
2. Fill in the enrollment code form:
   - **Client**: Select the client (node) this device will use
   - **Validity Period**: Choose how long the code remains valid (1-168 hours)
     - Default: 24 hours
     - Maximum: 168 hours (7 days)
   - **Device Name/Notes** (optional): Enter a description like "John's iPhone" for tracking
3. Click **"Generate Code"**

### Step 3: Share the Enrollment Code

After generating the code, you'll see a QR code and enrollment URL. You can:

**Option A: QR Code (Recommended)**
- Show the QR code on your screen
- Have the user scan it with their Mobile Nebula app

**Option B: Enrollment URL**
- Click "Copy URL" to copy the enrollment link
- Share it via email, chat, or other secure method
- User can paste it directly into the Mobile Nebula app

**Option C: Code Only**
- Click "Copy" next to the code string
- Share the code with the user
- User can manually enter it in the app (not recommended, codes are long)

### Step 4: Monitor Enrollment Status

Back on the Mobile Enrollment page, you can see all enrollment codes with their status:

- **Active** (yellow): Code has not been used yet and is not expired
- **Used** (green): Device has successfully enrolled using this code
- **Expired** (red): Code has passed its expiration time

Once a device enrolls:
- The code status changes to "Used"
- Device information appears (device name, platform like "iOS" or "Android")
- The code can no longer be used by other devices

### Managing Enrollment Codes

**Delete Unused Codes:**
- Click the trash icon next to an Active or Expired code to delete it
- Used codes cannot be deleted (they serve as an audit trail)

**Time Remaining:**
- Active codes show how much time is left before expiration
- Examples: "23h 45m remaining", "2 days remaining"

## For End Users: Enrolling Your Device

### Prerequisites

1. Install the Mobile Nebula app from the App Store (iOS) or Google Play (Android)
2. Receive an enrollment code, QR code, or enrollment URL from your administrator

### Enrollment Methods

#### Method 1: QR Code Scanning (Easiest)

1. Open the Mobile Nebula app
2. Tap **"Add Network"** or the **+** button
3. Select **"Enroll using QR code"** or similar option
4. Point your camera at the QR code displayed by your administrator
5. The app will automatically:
   - Download your network configuration
   - Generate a secure key pair on your device
   - Request and install your certificate
   - Configure the Nebula connection
6. Tap **"Connect"** to start the VPN

#### Method 2: Enrollment URL

1. Receive the enrollment URL from your administrator (e.g., via email)
2. Open the Mobile Nebula app
3. Tap **"Add Network"** or the **+** button
4. Select **"Enroll using URL"** or similar option
5. Paste the enrollment URL when prompted
6. The app will complete the enrollment automatically
7. Tap **"Connect"** to start the VPN

### After Enrollment

Once enrolled, your device will:
- Appear in the administrator's dashboard
- Have a valid Nebula certificate
- Be able to connect to other nodes in the mesh network
- Automatically manage certificate rotation (handled by Managed Nebula)

### Troubleshooting

**"Invalid enrollment code" error:**
- The code may have expired (default: 24 hours)
- The code may have already been used
- Ask your administrator to generate a new code

**"Network error" during enrollment:**
- Check your internet connection
- Verify you can reach the Managed Nebula server URL
- Contact your administrator

**Certificate or configuration issues:**
- The client may not have an IP assignment
- Contact your administrator to check the client configuration

## Security Considerations

### For Administrators

1. **Expiration Times**: Use shorter validity periods (1-24 hours) for higher security
2. **Secure Sharing**: Share codes via secure channels (encrypted chat, in-person)
3. **Monitor Usage**: Regularly review the enrollment codes list for suspicious activity
4. **Delete Unused Codes**: Delete codes that are no longer needed
5. **Audit Trail**: Used codes remain visible for audit purposes

### For End Users

1. **Don't Share Codes**: Your enrollment code is like a password - don't share it
2. **Use Quickly**: Enroll your device as soon as you receive the code
3. **Secure Your Device**: Protect your device with a passcode/biometric lock
4. **Report Issues**: If you suspect your code was compromised, contact your administrator immediately

## Technical Details

### How It Works

1. **Code Generation**:
   - Server generates a cryptographically secure 64-character token
   - Code is associated with a specific client and expiration time
   - QR code encodes the full enrollment URL

2. **Key Generation**:
   - Mobile app generates an Ed25519 key pair locally on the device
   - Private key never leaves the device
   - Public key is sent to the server during enrollment

3. **Certificate Issuance**:
   - Server signs a Nebula certificate using the device's public key
   - Certificate includes the client's IP address and group memberships
   - Certificate is valid for 6 months (configurable)

4. **One-Time Use**:
   - Server marks the code as "used" immediately after successful enrollment
   - Code cannot be reused, preventing unauthorized access

### Comparison with Traditional Methods

| Feature | Manual Configuration | Mobile Enrollment |
|---------|---------------------|-------------------|
| Setup Time | 15-30 minutes | 1-2 minutes |
| Technical Knowledge Required | High | Low |
| Certificate Management | Manual | Automatic |
| Error Prone | Yes | No |
| Secure Key Generation | Manual (risk of exposure) | Automatic (keys stay on device) |
| Scalability | Poor (manual steps) | Excellent (one-click) |

## Best Practices

### For IT Teams

1. **Standard Operating Procedure**:
   - Create a standard workflow for mobile device enrollment
   - Document the process for different device types
   - Train help desk staff on generating and troubleshooting codes

2. **Batch Enrollment**:
   - For onboarding multiple users, generate codes in advance
   - Track codes in a spreadsheet with user names and expiration times
   - Consider using longer validity periods (48-72 hours) for flexibility

3. **Security Policy**:
   - Set organization-wide validity period standards
   - Require re-enrollment for lost or stolen devices
   - Implement device management policies (MDM integration)

4. **Monitoring**:
   - Regularly review enrolled devices
   - Set up alerts for suspicious enrollment patterns
   - Track certificate expiration dates

### For Users

1. **Enroll ASAP**: Don't wait until your code expires
2. **Test Connection**: Verify you can reach network resources after enrollment
3. **Keep App Updated**: Update Mobile Nebula when new versions are released
4. **Report Problems**: Contact your IT team if you have connection issues

## FAQ

### Q: How long does an enrollment code last?
**A:** By default, 24 hours. Your administrator can configure it from 1 hour to 7 days.

### Q: Can I reuse an enrollment code?
**A:** No, each code can only be used once for security reasons.

### Q: What happens if my code expires before I use it?
**A:** Ask your administrator to generate a new code.

### Q: Can I enroll multiple devices with the same code?
**A:** No, each device needs its own unique enrollment code.

### Q: What information does the server see during enrollment?
**A:** The server sees:
- Device name (if you provide it)
- Device ID (generated by the app)
- Platform (iOS or Android)
- The public key (not the private key)

### Q: Is my private key sent to the server?
**A:** No! Your private key is generated on your device and never leaves it. Only the public key is sent to the server.

### Q: How often do I need to re-enroll?
**A:** Certificates are valid for 6 months and are automatically rotated by Managed Nebula. You typically don't need to re-enroll unless:
- You get a new device
- Your device is lost or stolen
- You're instructed to by your administrator

### Q: Can I use this for desktop/laptop computers?
**A:** This enrollment method is designed for the Mobile Nebula app. Desktop/laptop computers should use the traditional client agent method.

## Support

For technical issues or questions:
1. Check the Managed Nebula documentation
2. Contact your network administrator
3. Submit an issue on the [GitHub repository](https://github.com/kumpeapps/managed-nebula)

## References

- [Mobile Nebula App (iOS)](https://apps.apple.com/app/mobile-nebula/id1509587936)
- [Mobile Nebula App (Android)](https://play.google.com/store/apps/details?id=net.defined.mobile_nebula)
- [Managed Nebula API Documentation](API_DOCUMENTATION.md)
- [Nebula Mesh VPN](https://github.com/slackhq/nebula)
