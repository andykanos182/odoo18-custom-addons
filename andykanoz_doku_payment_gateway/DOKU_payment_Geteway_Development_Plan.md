# DOKU Payment Gateway - Odoo 18 Development Plan

**Project**: DOKU Payment Gateway Integration for Odoo 18  
**Module Name**: `doku_payment_gateway`  
**Version**: 1.0.0  
**Status**: Planning Phase  
**Timeline**: 5 Weeks  
**Last Updated**: April 27, 2026

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Technical Architecture](#technical-architecture)
3. [Module Structure](#module-structure)
4. [Phase-by-Phase Breakdown](#phase-by-phase-breakdown)
5. [Database Models](#database-models)
6. [API Integration Points](#api-integration-points)
7. [File Structure](#file-structure)
8. [Dependencies & Requirements](#dependencies--requirements)
9. [Configuration & Setup](#configuration--setup)
10. [Testing Strategy](#testing-strategy)

---

## 📚 Project Overview

### Objectives
- ✅ Integrate DOKU payment gateway with Odoo 18 e-commerce module
- ✅ Support multiple payment methods (QRIS, Virtual Account, Credit Card, E-wallet)
- ✅ Enable real-time payment status tracking via webhooks
- ✅ Auto-validate invoices upon successful payment
- ✅ Provide comprehensive transaction logging and reporting
- ✅ Maintain PCI DSS compliance (sensitive data never stored locally)

### Key Features
| Feature | Status | Priority |
|---------|--------|----------|
| QRIS Payment Support | TBD | High |
| Virtual Account (Bank Transfer) | TBD | High |
| Credit Card Payment | TBD | High |
| E-wallet Integration (OVO/DANA/GoPay) | TBD | Medium |
| Webhook Payment Notifications | TBD | High |
| Auto-Invoice Reconciliation | TBD | High |
| Payment Journal Recording | TBD | High |
| Sandbox/Test Mode Support | TBD | High |
| Transaction History & Reporting | TBD | Medium |
| Refund Processing | TBD | Medium |
| Payment Token/Save Card | TBD | Low |

### Constraints & Assumptions
- DOKU API credentials will be obtained after account verification
- Odoo 18 is installed at `D:\MyServer\Odoo18\`
- Module will be placed in `D:\MyServer\Odoo18\Addons\doku_payment_gateway\`
- PostgreSQL database available and accessible
- Python 3.10+ with required packages (requests, cryptography)
- HTTPS/SSL required for production webhooks

---

## 🏗️ Technical Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                       ODOO 18                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Website / eCommerce Module                          │   │
│  │  - Shopping Cart                                      │   │
│  │  - Checkout Flow                                      │   │
│  └────────────────────┬─────────────────────────────────┘   │
│                       │                                       │
│  ┌────────────────────▼─────────────────────────────────┐   │
│  │  DOKU Payment Gateway Module (This Module)           │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ Payment Acquirer (Provider Config)              │ │   │
│  │  │ - Credentials Management                        │ │   │
│  │  │ - Test/Live Mode Toggle                         │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ Payment Methods (QRIS / VA / Card / Wallet)    │ │   │
│  │  │ - Method Selection                              │ │   │
│  │  │ - Payment Request Formation                     │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ API Integration Layer                           │ │   │
│  │  │ - HTTP Requests to DOKU                         │ │   │
│  │  │ - Response Parsing                              │ │   │
│  │  │ - Error Handling & Retry Logic                  │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ Webhook Handler                                 │ │   │
│  │  │ - Payment Status Notifications                  │ │   │
│  │  │ - Transaction Recording                         │ │   │
│  │  │ - Invoice Auto-Validation                       │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                       │                                       │
└───────────────────────┼───────────────────────────────────────┘
                        │
                        │ HTTP/HTTPS API Calls
                        │
            ┌───────────▼───────────┐
            │   DOKU API Server     │
            │ (Sandbox/Production)  │
            │                       │
            │ - Create Payment      │
            │ - Check Status        │
            │ - Process Refund      │
            │ - Send Notifications  │
            └───────────────────────┘
```

### Technology Stack
- **Framework**: Odoo 18 (Python/PostgreSQL)
- **HTTP Client**: `requests` library (for API calls)
- **Encryption**: `cryptography` (for signature generation)
- **Security**: SSL/TLS, HMAC-SHA256 signatures
- **Database**: PostgreSQL (Odoo's default)
- **API Protocol**: RESTful JSON over HTTPS

### Data Flow (Happy Path)

1. **Customer Initiates Payment**
   - Customer selects payment method (QRIS, VA, Card, etc.)
   - Odoo creates payment transaction record

2. **Payment Request to DOKU**
   - Module sends payment request to DOKU API with:
     - Order details (amount, invoice number)
     - Payment method preference
     - Callback URL for notifications
   - DOKU responds with payment reference & status

3. **Customer Makes Payment**
   - Customer scans QRIS / enters VA / swipes card
   - Payment processor handles transaction
   - DOKU records payment received

4. **Webhook Notification**
   - DOKU sends webhook notification to Odoo
   - Webhook handler verifies signature
   - Transaction status updated to "confirmed"
   - Invoice auto-validated if configured

5. **Reconciliation**
   - Payment journal entry created
   - Settlement recorded in accounting
   - Customer receives receipt/confirmation

---

## 📁 Module Structure

### Directory Layout

```
doku_payment_gateway/
├── __init__.py                          # Package init
├── __manifest__.py                      # Module metadata
├── models/
│   ├── __init__.py
│   ├── payment_acquirer.py             # Payment provider config
│   ├── payment_transaction.py           # Transaction handling
│   └── payment_method.py                # Payment method definitions
├── controllers/
│   ├── __init__.py
│   └── webhook.py                       # Webhook receiver
├── views/
│   ├── __init__.py
│   ├── payment_acquirer_views.xml       # Configuration UI
│   ├── payment_transaction_views.xml    # Transaction tracking UI
│   └── dashboard.xml                    # Payment dashboard
├── data/
│   ├── __init__.py
│   ├── payment_methods.xml              # QRIS, VA, Card method definitions
│   └── account_journal_data.xml         # Journal configuration
├── static/
│   ├── description/
│   │   └── icon.png                     # Module icon
│   └── src/
│       └── js/
│           └── payment_widget.js        # Frontend payment selector
├── security/
│   ├── __init__.py
│   └── ir_model_access.xml              # Access control
├── utils/
│   ├── __init__.py
│   ├── api_client.py                    # DOKU API wrapper
│   ├── signature.py                     # HMAC signature generation
│   ├── exceptions.py                    # Custom exceptions
│   └── logger.py                        # Logging configuration
├── tests/
│   ├── __init__.py
│   ├── test_api_client.py               # API integration tests
│   ├── test_payment_flow.py             # End-to-end tests
│   └── test_webhook.py                  # Webhook handling tests
├── documentation/
│   ├── SETUP.md                         # Installation guide
│   ├── API_DOCS.md                      # API documentation
│   ├── CONFIGURATION.md                 # Configuration guide
│   └── TROUBLESHOOTING.md               # Troubleshooting guide
└── README.md                            # Project readme
```

---

## 📊 Phase-by-Phase Breakdown

### Phase 1: Foundation Setup (Week 1)
**Goal**: Establish module structure and core models  
**Duration**: 5 days  
**Deliverables**: Module framework, database schema, configuration UI

#### Tasks:
- [x] Create module directory structure
- [x] Write `__manifest__.py` with dependencies
- [x] Define payment acquirer model
- [x] Create payment transaction model
- [x] Build configuration form/view
- [x] Setup database migrations
- [x] Create initial security rules
- [x] Documentation: Setup guide

**Key Files to Create**:
- `__manifest__.py` - Module metadata
- `models/payment_acquirer.py` - Provider configuration
- `models/payment_transaction.py` - Transaction tracking
- `views/payment_acquirer_views.xml` - Configuration UI

**Estimated Effort**: 16 hours

---

### Phase 2: Payment Methods (Week 2)
**Goal**: Implement support for all DOKU payment methods  
**Duration**: 5 days  
**Deliverables**: QRIS, VA, Card, E-wallet payment methods

#### Payment Methods to Support:

**1. QRIS (Quick Response Code Indonesian Standard)**
- Dynamic QR code generation
- Real-time amount validation
- QR expiry configuration (default: 60 minutes)
- Automatic status polling

**2. Virtual Account (Bank Transfer)**
- Bank selection (BRI, BCA, Mandiri, BTN, etc.)
- Dynamic VA number generation per transaction
- VA expiry time configuration
- Bank inquiry support (for direct confirmation)

**3. Credit Card**
- Card tokenization support
- 3D Secure authentication
- Installment options (3/6/12 months)
- CVV validation

**4. E-wallet (OVO, DANA, GoPay)**
- Multi-wallet support in single transaction
- Wallet brand selection
- Real-time wallet balance check
- Wallet ID association

#### Tasks:
- [x] Define payment method models
- [x] Create QRIS payment handler
- [x] Create VA payment handler
- [x] Create Card payment handler
- [x] Create E-wallet payment handler
- [x] Build payment method selection UI
- [x] Implement amount/currency validation
- [x] Create payment method test suite

**Key Files to Create**:
- `models/payment_method.py` - Payment method definitions
- `data/payment_methods.xml` - Method data
- `views/payment_method_views.xml` - UI forms

**Estimated Effort**: 20 hours

---

### Phase 3: API Integration (Week 3)
**Goal**: Implement DOKU API communication layer  
**Duration**: 5 days  
**Deliverables**: API wrapper, request/response handling, security

#### Core API Operations:

**Payment Initiation**
```
POST /api/payment/checkout/process
Request: {
  order.invoice_number,
  order.amount,
  payment_method_type,
  customer.email,
  customer.phone,
  callback_url
}
Response: {
  payment.reference_id,
  payment.status,
  payment.redirect_url (for hosted checkout)
}
```

**Payment Status Check**
```
GET /api/payment/checkout/{reference_id}
Response: {
  status: "pending" | "paid" | "failed" | "cancelled"
  amount_paid,
  paid_at,
  payment_method_used
}
```

**Refund Processing**
```
POST /api/payment/{reference_id}/refund
Request: { amount, reason }
Response: { refund_id, refund_status }
```

#### Tasks:
- [x] Create DOKU API client wrapper
- [x] Implement HMAC-SHA256 signature generation
- [x] Create payment request builder
- [x] Implement status check polling
- [x] Create refund request handler
- [x] Implement error handling & retry logic
- [x] Setup request/response logging
- [x] Create API exception classes

**Key Files to Create**:
- `utils/api_client.py` - DOKU API wrapper
- `utils/signature.py` - Signature generation
- `utils/exceptions.py` - Custom exceptions

**Estimated Effort**: 18 hours

---

### Phase 4: Webhook & Callbacks (Week 4)
**Goal**: Handle payment notifications and auto-reconciliation  
**Duration**: 5 days  
**Deliverables**: Webhook handler, transaction updates, invoice validation

#### Webhook Notifications from DOKU:

**Payment Confirmation**
```
POST /payment/webhook/confirm
Headers: {
  X-Signature: "HMAC-SHA256 signature"
}
Body: {
  order.invoice_number,
  payment.reference_id,
  payment.status: "success",
  payment.amount,
  payment.method,
  timestamp
}
```

**Payment Failed**
```
POST /payment/webhook/failed
Body: {
  order.invoice_number,
  payment.reference_id,
  payment.status: "failed",
  error_code,
  error_message,
  timestamp
}
```

#### Tasks:
- [x] Create webhook controller
- [x] Implement signature verification
- [x] Create payment confirmation handler
- [x] Create payment failure handler
- [x] Implement transaction status updater
- [x] Create auto-invoice validation logic
- [x] Implement payment journal entry creation
- [x] Setup webhook retry mechanism
- [x] Create webhook execution logs

**Key Files to Create**:
- `controllers/webhook.py` - Webhook handler
- `models/webhook_log.py` - Webhook execution tracking

**Estimated Effort**: 16 hours

---

### Phase 5: Testing & Deployment (Week 5)
**Goal**: Comprehensive testing and production readiness  
**Duration**: 5 days  
**Deliverables**: Test coverage, documentation, deployment guide

#### Testing Strategy:

**Unit Tests**
- API client tests
- Signature generation tests
- Payment method logic tests
- Exception handling tests

**Integration Tests**
- Sandbox API communication
- Payment flow end-to-end
- Webhook handling
- Invoice reconciliation

**Manual Testing**
- Sandbox QRIS payment
- Sandbox VA payment
- Sandbox Card payment
- Webhook notification simulation
- Error scenarios

#### Tasks:
- [x] Write comprehensive unit tests
- [x] Write integration tests
- [x] Test error scenarios
- [x] Perform sandbox testing
- [x] Write setup documentation
- [x] Write API documentation
- [x] Write troubleshooting guide
- [x] Code review & cleanup
- [x] Version control setup

**Key Files to Create**:
- `tests/` - Test suite
- `documentation/SETUP.md` - Installation guide
- `documentation/API_DOCS.md` - API documentation

**Estimated Effort**: 14 hours

---

## 💾 Database Models

### 1. Payment Acquirer Model
**Odoo Model**: `payment.provider` (extended)

```python
Fields:
- code: char = "doku"  # Provider identifier
- name: char = "DOKU Payment Gateway"
- state: selection = "test" | "enabled"
- doku_merchant_code: char  # Merchant ID from DOKU
- doku_api_key: char  # API Key (encrypted)
- doku_api_secret: char  # API Secret (encrypted)
- doku_sandbox_mode: boolean = True
- support_currencies: Many2many (allowed currencies)
- payment_method_ids: One2many (supported methods)
- journal_id: Many2one (account.journal)  # Payment journal
```

### 2. Payment Transaction Model
**Odoo Model**: `payment.transaction` (extended)

```python
Fields:
- provider_id: Many2one (payment.provider)
- amount: decimal
- currency_id: Many2one (res.currency)
- reference: char  # Odoo reference
- doku_reference_id: char  # DOKU payment reference
- payment_method: selection = "qris" | "va" | "card" | "wallet"
- state: selection = "draft" | "pending" | "done" | "error" | "cancel"
- metadata: json  # Additional data (QR code, VA number, etc.)
- error_code: char
- error_message: text
- paid_at: datetime
- webhook_count: integer  # Webhook attempt count
- last_webhook_at: datetime
- transaction_logs: One2many (payment.transaction.log)
```

### 3. Payment Transaction Log
**New Model**: `payment.transaction.log`

```python
Fields:
- transaction_id: Many2one (payment.transaction)
- log_type: selection = "api_request" | "api_response" | "webhook" | "status_check"
- request_body: text  # Full request (for debugging)
- response_body: text  # Full response
- http_status: integer
- error_message: text
- created_at: datetime
- ip_address: char  # Webhook source IP
```

### 4. Payment Method Model
**Odoo Model**: `payment.method` (extended)

```python
Fields:
- provider_id: Many2one (payment.provider)
- name: char = "QRIS" | "Virtual Account" | "Credit Card" | "E-wallet"
- method_type: char = "qris" | "va" | "card" | "wallet"
- is_active: boolean = True
- description: text
- icon: binary
```

### 5. Bank Configuration
**New Model**: `doku.bank.config`

```python
Fields:
- bank_code: char  # BRI, BCA, Mandiri, etc.
- bank_name: char
- logo_url: char
- is_active: boolean = True
- min_amount: decimal
- max_amount: decimal
```

---

## 🔌 API Integration Points

### DOKU API Endpoints

**Base URL**:
- Sandbox: `https://sandbox.doku.com`
- Production: `https://api.doku.com`

**Main Endpoints**:

1. **Create Payment**
   ```
   POST /api/payment/checkout/process
   ```

2. **Check Payment Status**
   ```
   GET /api/payment/checkout/{reference_id}
   ```

3. **Refund Payment**
   ```
   POST /api/payment/{reference_id}/refund
   ```

4. **Query Transaction History**
   ```
   GET /api/payment/history
   ```

5. **Webhook Callback** (Incoming)
   ```
   POST /payment/webhook/confirm
   ```

### Authentication

**Method**: HMAC-SHA256 Signature

**Signature Generation**:
```
signature = HMAC-SHA256(
  key = api_secret,
  message = merchant_code + amount + reference_id + timestamp
)

Header: X-Signature: {signature}
```

---

## ⚙️ Configuration & Setup

### Installation Steps

1. **Place Module**
   ```bash
   cp -r doku_payment_gateway D:\MyServer\Odoo18\Addons\
   ```

2. **Install Module in Odoo**
   - Go to: Apps → Search "DOKU Payment Gateway"
   - Click Install

3. **Configure Payment Provider**
   - Go to: Accounting → Configuration → Payment Providers
   - Create new provider
   - Fill in:
     - Provider: "DOKU"
     - Merchant Code (from DOKU dashboard)
     - API Key (from DOKU dashboard)
     - API Secret (from DOKU dashboard)
     - Toggle Test Mode (initially true)

4. **Select Payment Methods**
   - Check: QRIS, Virtual Account, Credit Card, E-wallet
   - Configure expiry times and limits

5. **Setup Webhook URL**
   - Go to: DOKU Dashboard → Settings → API
   - Set Webhook URL: `https://yourdomain.com/payment/webhook/confirm`
   - DOKU will send payment notifications to this URL

6. **Test**
   - Create test order
   - Select DOKU as payment method
   - Use DOKU sandbox credentials to test payment
   - Verify webhook notification received

---

## 📦 Dependencies & Requirements

### Python Packages
```
requests>=2.28.0           # HTTP client
cryptography>=38.0.0       # Encryption
pytz>=2022.1               # Timezone handling
python-dateutil>=2.8.2     # Date utilities
```

### Odoo Modules (Dependencies)
```
- sale
- website_sale
- account
- payment
- website
```

### System Requirements
- Python 3.10+
- PostgreSQL 12+
- HTTPS/SSL certificate (for production)
- Internet connection (for API calls)

### DOKU Requirements
- DOKU merchant account (verified)
- API credentials (Merchant Code, API Key, API Secret)
- Sandbox environment for testing
- Webhook notification capability

---

## 📝 Testing Strategy

### Unit Tests Coverage

**API Client Tests**
- Signature generation correctness
- Request formatting
- Response parsing
- Error handling

**Payment Method Tests**
- Amount validation
- Currency handling
- Method-specific logic

**Webhook Tests**
- Signature verification
- Payload parsing
- State transitions

### Integration Tests

**End-to-End Flow**
1. Create order
2. Initiate QRIS payment → get QR code
3. Simulate payment completion
4. Receive webhook notification
5. Verify transaction status updated
6. Verify invoice auto-validated
7. Verify payment journal entry created

### Manual Testing Checklist

- [ ] QRIS payment (scan QR → payment complete)
- [ ] VA payment (transfer → payment complete)
- [ ] Card payment (enter card → 3D Secure → complete)
- [ ] E-wallet payment (OVO/DANA → payment complete)
- [ ] Webhook notification received
- [ ] Failed payment scenario
- [ ] Refund processing
- [ ] Error logging
- [ ] Transaction reconciliation

---

## 📅 Development Timeline

| Phase | Duration | Start | End | Status |
|-------|----------|-------|-----|--------|
| Phase 1: Foundation | 5 days | Week 1 | - | Planned |
| Phase 2: Payment Methods | 5 days | Week 2 | - | Planned |
| Phase 3: API Integration | 5 days | Week 3 | - | Planned |
| Phase 4: Webhooks | 5 days | Week 4 | - | Planned |
| Phase 5: Testing & Docs | 5 days | Week 5 | - | Planned |
| **Total** | **25 days** | | | |

---

## 📚 Documentation Checklist

- [ ] Installation Guide (SETUP.md)
- [ ] Configuration Guide (CONFIGURATION.md)
- [ ] API Documentation (API_DOCS.md)
- [ ] Troubleshooting Guide (TROUBLESHOOTING.md)
- [ ] Developer Guide
- [ ] Module README.md
- [ ] Code Comments & Docstrings
- [ ] Database Schema Documentation

---

## ✅ Success Criteria

- ✅ Module successfully integrated with Odoo 18
- ✅ All 4 payment methods functional (QRIS, VA, Card, E-wallet)
- ✅ Webhook notifications working reliably
- ✅ Auto-invoice validation on payment success
- ✅ 90%+ test coverage
- ✅ Complete documentation
- ✅ Error handling for all edge cases
- ✅ Production-ready code quality

---

## 🔒 Security Considerations

1. **API Credentials**
   - Store encrypted in database
   - Never log to console/file
   - Rotate periodically

2. **Sensitive Data**
   - Never store card numbers (use tokenization)
   - Never store customer bank details
   - Use SSL/TLS for all API calls

3. **Webhook Security**
   - Verify HMAC signature on all webhooks
   - Implement rate limiting
   - Log all webhook attempts
   - Validate source IP if possible

4. **PCI Compliance**
   - Delegate card data to DOKU (PCI DSS certified)
   - Use DOKU tokenization for saved cards
   - Regular security audits

---

## 📞 Support & Maintenance

### Regular Tasks
- Monitor API error rates
- Review transaction logs
- Reconcile payments daily
- Update DOKU API if new versions released

### Troubleshooting Resources
- DOKU API Documentation: https://developers.doku.com/
- DOKU Dashboard: https://dashboard.doku.com/
- Odoo Payment Provider Docs: https://www.odoo.com/documentation/18.0/applications/finance/payment_providers.html

---

**End of Development Plan**

Generated: April 27, 2026
