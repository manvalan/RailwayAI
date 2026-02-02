# 🛡️ App Store & GDPR Compliance Fact Sheet

This document provides technical information regarding the security and privacy measures implemented in the Railway AI backend. It is designed to assist in the App Store Review process and demonstrate GDPR compliance.

---

## 1. Data Privacy & User Control (Apple Guideline 5.1.1)

### Account Deletion
In accordance with Apple's requirements for apps that support account creation, Railway AI provides a dedicated endpoint for users to permanently delete their accounts and all associated personal data.
- **Endpoint**: `DELETE /api/v1/user/me`
- **Effect**: Performs a permanent removal of the user record, including email, hashed password, and API keys from the production database.

### Consent Tracking
Every user registration is bound to an explicit acceptance of the Terms of Service and Privacy Policy.
- **Audit Trail**: The system records the exact timestamp of consent in the `terms_accepted_at` field within the database.
- **Transparency**: Terms are accessible publicly at `/static/terms.html`.

---

## 2. Security Infrastructure

### Data Storage & Encryption
- **Passwords**: User passwords are never stored in plain text. We utilize **Bcrypt** (key-stretching algorithm) with a secure salt to hash passwords before storage.
- **Authentication**: The system uses **long-lived API Keys** (60-day rotation) or JWT tokens for secure session management, minimizing the transmission of raw credentials.

### Access Control (RBAC)
Railway AI implements strict **Role-Based Access Control**. 
- Users are assigned privilege levels (`admin`, `proof`, `normal`, `guest`).
- Critical operations (e.g., scenario generation, AI training, system settings) are restricted to `admin` accounts via server-side middleware.

---

## 3. GDPR Compliance Details

| Requirement | Implementation in Railway AI |
| :--- | :--- |
| **Right to Erasure** | Handled via the `/api/v1/user/me` endpoint. |
| **Data Minimization** | We only collect the minimum necessary data: Username and Email. |
| **Integrity & Confidentiality** | Implemented through Bcrypt hashing and TLS-ready API nodes. |
| **Accountability** | All administrative actions are logged and broadcasted to authorized monitors via WebSockets. |

---

## 4. Technical Requirements for Production

For a successful App Store deployment, the following environment configurations are recommended:
1. **HTTPS/TLS**: Ensure the FastAPI server is behind a reverse proxy (like Nginx or Caddy) providing valid SSL certificates to satisfy Apple's **App Transport Security (ATS)**.
2. **SMTP Configuration**: Use the integrated SMTP settings panel in the admin dashboard to ensure secure delivery of verification codes via TLS/SSL.

---

**Document Version**: 1.0.0  
**Last Review**: February 2, 2026  
**Compliance Lead**: Railway AI Core Team
