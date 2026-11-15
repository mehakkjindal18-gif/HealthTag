
#  HealthTag prototype (Team Schrodinger's, Vivaan X 2026) - Emergency Medical Access Prototype

HealthTag is a QR-based emergency health identity system that provides controlled access to medical information during emergencies. Bystanders can view emergency contact details, verified doctors and paramedics can access an emergency medical card, and full medical history becomes available after the emergency contact approves access.

## Key Features

- **QR-based access:** Scan a HealthTag QR code to access emergency information.
- **Three-tier access control:** Provide different levels of medical information based on verification and approval.
- **Responder verification:** Verify doctor and paramedic credentials.
- **SMS-based verification:** Send verification codes and support emergency access approval through SMS.
- **Contact-approved history sharing:** Require approval before revealing full medical history.
- **Time-limited access:** Requests expire after 15 minutes, and approved full-history access expires after 30 minutes.
- **Activity logging:** Record scans, requests, approvals, and treatment notes.
- **Owner dashboard:** Review access activity and notifications.
- **Printable HealthTag:** Create a HealthTag and generate its printable card.
- **Cloud deployment:** Hosted on Render and accessible over the internet, including QR scanning across different networks.
- **CRSF Protection:** Additional security hardening, including CSRF protection.


## Emergency Access Levels

| Who scans the QR | What they can see |
|---|---|
| Anyone (no sign-in) | Emergency helpline 108 and the emergency contact's number. No name or medical data. |
| Verified doctor or paramedic | Emergency card containing blood group, allergies, conditions, and medications. Access is logged against their ID. |
| Same responder, after contact approval | Full medical history and hospital notes for 30 minutes. |

Every access event is recorded in an activity log, and the owner receives a notification.

## Getting Started

HealthTag is hosted on Render, so you can access the deployed application without installing Python or running a local server.

**Live application:** [HealthTag on Render] <[HealthTag](https://healthtag.onrender.com/)>

1. Open the deployed HealthTag application.
2. Create a HealthTag or open an existing QR code.
3. Scan the QR code using a phone camera or compatible QR scanner.
4. Follow the on-screen instructions to access the appropriate level of emergency information.

**Network compatibility:** The QR code can be scanned across different networks. The device displaying the QR code and the scanning device do not need to be connected to the same Wi-Fi network. Both devices need internet access to reach the hosted application.

## Demo Walkthrough

1. Open the HealthTag application and scan its QR code. The public view displays only the emergency helpline and contact number.
2. Select **Verify and open the medical card** and sign in using a demo account:
   - **Doctor:** `H-1001 / 1234` — Dr. Anita Verma, Apollo Hospital.
   - **Paramedic:** `A-2002 / 1234` —  Ravi Kumar, 108 Ambulance Service
3. Select **Request full history** to request access to the complete medical history.
4. Open the approval link or use the verification code delivered through the configured SMS workflow.
5. Approve the request to unlock full-history access for the permitted duration.
6. Add a treatment note on the responder screen.
7. Open the **Owner dashboard** to review scans, requests, approvals, and notes.
8. Select **Create a HealthTag**, complete the form, and display the printable card.

*The listed credentials are demonstration accounts and should not be used as real medical credentials.*

## Implementation Status

HealthTag implements the following functionality:

- Three-tier emergency access.
- Credential verification using hashed PINs.
- One-time verification codes with up to three attempts.
- SMS-based verification and access approval workflows.
- Approval links for emergency contact authorization.
- Request expiry after 15 minutes.
- Full-history access expiry after 30 minutes.
- Activity logging and owner notifications.
- Hospital notes and QR code generation.
- Encryption of medical fields when the required cryptography dependency is available.
- Render deployment for internet-based access and cross-network QR scanning.

## Future Improvements

Potential enhancements include:

- ABHA integration.
- Further testing of security, reliability, and production readiness.

HealthTag is a working prototype demonstrating controlled access to emergency medical information. It should undergo appropriate security and reliability testing before being used for real medical emergencies.

## Project Structure

| File or directory | Purpose |
|---|---|
| `app.py` | Backend routes, access rules, and database operations. |
| `templates/` | Application interface templates. |
| `static/style.css` | Interface styling. |
| `requirements.txt` | Python dependencies. |
| `healthtag.db` | Local database, when created. |
| `.healthtag.key`, `.secret_key` | Local key and secret files, when created. |

**Security note:** Never commit real secrets, encryption keys, or sensitive medical data to a public repository. Keep sensitive local files out of version control.

---

*HealthTag — controlled access to emergency medical information.*
