# DOKU Payment Gateway - Sprint Tasks & Detailed Breakdown

---

## 🎯 Sprint 1: Foundation Setup (Week 1)

### Sprint Goals
- [x] Module structure created and tested
- [x] Core models defined with database migrations
- [x] Configuration UI functional
- [x] Security/ACL rules established
- [x] Basic testing framework setup

### Day 1-2: Module Scaffolding

**Task 1.1: Create Module Structure**
- Create directory: `D:\MyServer\Odoo18\Addons\doku_payment_gateway\`
- Create subdirectories: models/, controllers/, views/, utils/, tests/, data/, static/, security/, documentation/
- Create `__init__.py` files in each directory
- **Deliverable**: Complete directory tree
- **Effort**: 2 hours

**Task 1.2: Write `__manifest__.py`**
```python
{
    'name': 'DOKU Payment Gateway',
    'version': '1.0.0',
    'author': 'Your Name',
    'license': 'LGPL-3',
    'category': 'Accounting/Payment',
    'depends': ['payment', 'website_sale', 'account'],
    'data': [
        'security/ir_model_access.xml',
        'data/payment_methods.xml',
        'views/payment_acquirer_views.xml',
        'views/payment_transaction_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['requests', 'cryptography'],
    },
}
```
- **Deliverable**: Valid manifest file
- **Effort**: 1 hour

**Task 1.3: Define Payment Acquirer Model**
File: `models/payment_acquirer.py`
- Extend `payment.provider` model
- Add DOKU-specific fields:
  - `doku_merchant_code`
  - `doku_api_key` (encrypted)
  - `doku_api_secret` (encrypted)
  - `doku_sandbox_mode`
- Add configuration validation method
- **Deliverable**: Functional model with encryption
- **Effort**: 4 hours

**Task 1.4: Define Payment Transaction Model**
File: `models/payment_transaction.py`
- Extend `payment.transaction`
- Add fields:
  - `doku_reference_id`
  - `payment_method` (QRIS/VA/Card/Wallet)
  - `metadata` (JSON for QR code, VA number, etc.)
  - `webhook_count`, `last_webhook_at`
- Add status update methods
- **Deliverable**: Transaction tracking model
- **Effort**: 3 hours

### Day 3-4: Database & Views

**Task 1.5: Create Security Rules**
File: `security/ir_model_access.xml`
```xml
- payment.provider access (User can view, Manager can edit)
- payment.transaction access (User can view all, Manager full access)
```
- **Deliverable**: ACL rules
- **Effort**: 1 hour

**Task 1.6: Build Configuration UI**
File: `views/payment_acquirer_views.xml`
- Create form view for DOKU provider configuration
- Fields:
  - Provider name
  - Test/Live mode toggle
  - Merchant code
  - API key (password field)
  - API secret (password field)
  - Supported currencies
  - Payment methods selection
- **Deliverable**: Working configuration form
- **Effort**: 3 hours

**Task 1.7: Build Transaction Tracking UI**
File: `views/payment_transaction_views.xml`
- Create list view for transactions
  - Columns: Reference, DOKU ID, Amount, Method, Status, Date
- Create form view for transaction details
  - Display all fields
  - Show transaction logs
  - Show metadata (QR code image if QRIS)
- **Deliverable**: Transaction UI
- **Effort**: 3 hours

### Day 5: Testing Framework & Documentation

**Task 1.8: Setup Test Infrastructure**
File: `tests/__init__.py` and `tests/test_api_client.py`
- Create test class structure
- Setup fixtures for mock DOKU API responses
- Create helper functions
- **Deliverable**: Test framework ready
- **Effort**: 2 hours

**Task 1.9: Write Setup Documentation**
File: `documentation/SETUP.md`
- Installation steps
- Configuration steps
- Initial verification
- **Deliverable**: Setup guide
- **Effort**: 1 hour

**Task 1.10: Code Review & Cleanup**
- Review all code for PEP 8 compliance
- Remove debug code
- Add docstrings
- **Deliverable**: Production-ready code
- **Effort**: 2 hours

**Sprint 1 Total Effort**: ~25 hours

---

## 🎯 Sprint 2: Payment Methods (Week 2)

### Sprint Goals
- [x] All 4 payment methods implemented
- [x] Payment method selection UI working
- [x] Amount/currency validation complete
- [x] Payment method test coverage 90%+

### Day 1-2: QRIS & Virtual Account

**Task 2.1: Implement QRIS Payment Handler**
File: `models/payment_qris.py`
- Create QRIS payment method class
- Implement:
  - QR code generation logic
  - Amount validation
  - Expiry time handling (default 60 minutes)
  - Dynamic QR for each transaction
- Store QR code in transaction metadata
- **Deliverable**: QRIS payment flow
- **Effort**: 4 hours

**Task 2.2: Implement Virtual Account Handler**
File: `models/payment_va.py`
- Create VA payment method class
- Implement:
  - Bank selection (dropdown from bank list)
  - Dynamic VA number generation
  - VA expiry time config
  - Bank inquiry support
- Store VA details in transaction metadata
- **Deliverable**: VA payment flow
- **Effort**: 4 hours

### Day 3-4: Credit Card & E-Wallet

**Task 2.3: Implement Credit Card Handler**
File: `models/payment_card.py`
- Create Card payment method class
- Implement:
  - Card tokenization logic (via DOKU)
  - 3D Secure configuration
  - Installment options (3/6/12 months)
  - CVV validation
  - Save card option
- Store card token (NOT card number)
- **Deliverable**: Card payment flow
- **Effort**: 4 hours

**Task 2.4: Implement E-Wallet Handler**
File: `models/payment_wallet.py`
- Create E-wallet payment method class
- Support: OVO, DANA, GoPay
- Implement:
  - Wallet brand selection
  - Real-time wallet availability check
  - Wallet ID association
- Store wallet preference in metadata
- **Deliverable**: E-wallet payment flow
- **Effort**: 3 hours

### Day 5: Payment Method Data & Testing

**Task 2.5: Create Payment Method Data**
File: `data/payment_methods.xml`
```xml
<record model="payment.method" id="qris">
  <field name="name">QRIS</field>
  <field name="method_type">qris</field>
  ...
</record>
<!-- Same for VA, Card, Wallet -->
```
- **Deliverable**: Method definitions in database
- **Effort**: 1 hour

**Task 2.6: Write Payment Method Tests**
File: `tests/test_payment_methods.py`
- Test QRIS validation
- Test VA creation
- Test Card tokenization
- Test Wallet selection
- Test amount validation
- **Deliverable**: 95%+ test coverage
- **Effort**: 3 hours

**Task 2.7: Build Method Selection UI**
File: `views/payment_method_selection.xml`
- Create payment method selection template
- Display icons for each method
- Show method details/description
- Handle user selection
- **Deliverable**: Method selector UI
- **Effort**: 2 hours

**Sprint 2 Total Effort**: ~25 hours

---

## 🎯 Sprint 3: API Integration (Week 3)

### Sprint Goals
- [x] DOKU API wrapper complete
- [x] All DOKU endpoints implemented
- [x] Signature generation working
- [x] Error handling & retry logic
- [x] API integration tests passing

### Day 1-2: API Wrapper & Authentication

**Task 3.1: Create API Client Wrapper**
File: `utils/api_client.py`
- Create `DokuAPIClient` class
- Constructor: `__init__(merchant_code, api_key, api_secret, sandbox=True)`
- Implement base HTTP request method
- Handle timeouts, retries, logging
- **Deliverable**: API client foundation
- **Effort**: 4 hours

**Task 3.2: Implement Signature Generation**
File: `utils/signature.py`
- Create `SignatureGenerator` class
- Implement HMAC-SHA256 signature generation
- Formula: `HMAC-SHA256(key=api_secret, message=...)`
- Add signature verification for webhooks
- **Deliverable**: Signature utilities
- **Effort**: 2 hours

**Task 3.3: Create Payment Request Builder**
- In `DokuAPIClient`:
  - Method `create_payment(order_data, payment_method)`
  - Builds JSON payload
  - Validates required fields
  - Sends to DOKU API
  - Returns payment reference & redirect URL
- Handle response parsing
- **Deliverable**: Payment creation flow
- **Effort**: 3 hours

### Day 3-4: API Operations

**Task 3.4: Implement Status Check**
- In `DokuAPIClient`:
  - Method `check_payment_status(reference_id)`
  - GET request to DOKU API
  - Parse response
  - Return status: pending/paid/failed/cancelled
  - **Deliverable**: Status polling
  - **Effort**: 2 hours

**Task 3.5: Implement Refund Processing**
- In `DokuAPIClient`:
  - Method `refund_payment(reference_id, amount, reason)`
  - Send refund request to DOKU
  - Track refund status
  - Store refund reference
  - **Deliverable**: Refund flow
  - **Effort**: 2 hours

**Task 3.6: Error Handling & Retry Logic**
File: `utils/exceptions.py`
- Define custom exceptions:
  - `DokuAPIError`
  - `DokuAuthenticationError`
  - `DokuTimeoutError`
  - `DokuValidationError`
- In `api_client.py`:
  - Implement exponential backoff retry
  - Handle rate limiting
  - Log all errors
  - **Deliverable**: Robust error handling
  - **Effort**: 3 hours

### Day 5: Logging & Testing

**Task 3.7: Setup Request/Response Logging**
File: `utils/logger.py`
- Create `PaymentLogger` class
- Log all API requests/responses
- Separate sensitive data (API key, card numbers)
- Store logs in database (payment.transaction.log)
- **Deliverable**: Comprehensive logging
- **Effort**: 2 hours

**Task 3.8: Write API Integration Tests**
File: `tests/test_api_client.py`
- Mock DOKU API responses
- Test payment creation
- Test status checks
- Test refund processing
- Test error scenarios
- Test signature verification
- **Deliverable**: 95%+ test coverage
- **Effort**: 4 hours

**Sprint 3 Total Effort**: ~25 hours

---

## 🎯 Sprint 4: Webhooks & Reconciliation (Week 4)

### Sprint Goals
- [x] Webhook controller implemented
- [x] Payment notifications processed
- [x] Transaction status updated correctly
- [x] Auto-invoice validation working
- [x] Payment journal entries created

### Day 1-2: Webhook Handler

**Task 4.1: Create Webhook Controller**
File: `controllers/webhook.py`
- Create webhook route: `POST /payment/webhook/confirm`
- Receive DOKU webhook notifications
- Parse JSON payload
- Extract transaction reference
- **Deliverable**: Webhook endpoint
- **Effort**: 2 hours

**Task 4.2: Implement Signature Verification**
- In webhook handler:
  - Extract `X-Signature` header
  - Reconstruct message from payload
  - Verify signature using `SignatureGenerator`
  - Reject if signature invalid
  - Log failed verification attempts
  - **Deliverable**: Security-verified webhook
  - **Effort**: 2 hours

**Task 4.3: Implement Payment Confirmation Logic**
- When webhook received with `status: "success"`:
  - Find transaction by DOKU reference ID
  - Update transaction state to "done"
  - Record payment timestamp
  - Store payment method used
  - Log webhook event
  - **Deliverable**: Confirmed payments
  - **Effort**: 2 hours

### Day 3-4: Transaction Reconciliation

**Task 4.4: Implement Auto-Invoice Validation**
- When payment confirmed:
  - Find related sales order
  - Find related invoice
  - If configured, auto-validate invoice
  - Post account move
  - Send customer confirmation email
  - **Deliverable**: Auto-validation flow
  - **Effort**: 3 hours

**Task 4.5: Create Payment Journal Entry**
- When payment confirmed:
  - Get payment journal (from acquirer config)
  - Create account.payment record
  - Link to invoice
  - Create journal entry
  - Reconcile if applicable
  - **Deliverable**: Accounting integration
  - **Effort**: 3 hours

**Task 4.6: Implement Failed Payment Handler**
- When webhook received with `status: "failed"`:
  - Find transaction
  - Update state to "error"
  - Store error code & message
  - Mark invoice unpaid
  - Send customer failure notification
  - **Deliverable**: Failure handling
  - **Effort**: 2 hours

### Day 5: Logging & Testing

**Task 4.7: Create Webhook Transaction Log Model**
File: `models/webhook_log.py`
- Model: `payment.webhook.log`
- Fields:
  - transaction_id
  - log_type (api_request/response/webhook)
  - request_body
  - response_body
  - http_status
  - error_message
  - created_at
  - ip_address
- **Deliverable**: Audit trail model
- **Effort**: 2 hours

**Task 4.8: Write Webhook Tests**
File: `tests/test_webhook.py`
- Mock webhook payloads
- Test payment confirmation webhook
- Test payment failed webhook
- Test signature verification
- Test transaction state updates
- Test invoice validation
- Test journal entry creation
- **Deliverable**: Webhook test coverage
- **Effort**: 4 hours

**Sprint 4 Total Effort**: ~24 hours

---

## 🎯 Sprint 5: Testing, Documentation & Deployment (Week 5)

### Sprint Goals
- [x] 95%+ test coverage across module
- [x] Complete documentation
- [x] Production deployment guide
- [x] Code review passed
- [x] Module ready for live deployment

### Day 1-2: End-to-End Testing

**Task 5.1: Write End-to-End Tests**
File: `tests/test_end_to_end.py`
- Test complete QRIS payment flow:
  1. Create order
  2. Select QRIS payment
  3. Generate QR
  4. Simulate payment
  5. Webhook notification
  6. Verify transaction status
  7. Verify invoice updated
- Repeat for VA, Card, Wallet
- **Deliverable**: E2E test suite
- **Effort**: 4 hours

**Task 5.2: Test Error Scenarios**
File: `tests/test_error_scenarios.py`
- Network timeout
- API error responses
- Invalid signature
- Duplicate webhooks
- Missing required fields
- **Deliverable**: Error handling coverage
- **Effort**: 2 hours

**Task 5.3: Manual Sandbox Testing Checklist**
- [ ] Sandbox QRIS payment (end-to-end)
- [ ] Sandbox VA payment (end-to-end)
- [ ] Sandbox Card payment (end-to-end)
- [ ] Sandbox E-wallet payment (end-to-end)
- [ ] Failed payment scenario
- [ ] Refund processing
- [ ] Invoice reconciliation
- [ ] Payment journal entries
- [ ] Email notifications
- **Deliverable**: Verified functionality
- **Effort**: 4 hours

### Day 3: Documentation

**Task 5.4: Write Installation Guide**
File: `documentation/SETUP.md`
Sections:
- Prerequisites
- Installation steps
- Configuration steps
- DOKU account setup
- Webhook URL configuration
- Initial verification
- Troubleshooting
- **Deliverable**: Complete setup guide
- **Effort**: 2 hours

**Task 5.5: Write API Documentation**
File: `documentation/API_DOCS.md`
Sections:
- API architecture overview
- DOKU endpoint specifications
- Request/response examples
- Authentication/signatures
- Error codes & handling
- Rate limits
- **Deliverable**: API docs
- **Effort**: 2 hours

**Task 5.6: Write Configuration Guide**
File: `documentation/CONFIGURATION.md`
Sections:
- Payment provider setup
- Payment method configuration
- Currency configuration
- Journal configuration
- Webhook configuration
- Test vs Production
- **Deliverable**: Config guide
- **Effort**: 1 hour

**Task 5.7: Write Troubleshooting Guide**
File: `documentation/TROUBLESHOOTING.md`
Sections:
- Common issues & solutions
- Log file locations
- How to debug API errors
- How to debug webhook issues
- Signature verification failures
- **Deliverable**: Troubleshooting guide
- **Effort**: 1 hour

### Day 4: Code Quality

**Task 5.8: Code Review & Cleanup**
- Review all Python files for:
  - PEP 8 compliance
  - Naming conventions
  - Documentation/docstrings
  - Security issues
  - Performance issues
- Remove debug code
- Add missing comments
- **Deliverable**: Production-ready code
- **Effort**: 3 hours

**Task 5.9: Add Comprehensive Docstrings**
- Docstrings for all classes
- Docstrings for all methods
- Type hints where applicable
- Example usage
- **Deliverable**: Well-documented code
- **Effort**: 2 hours

### Day 5: Deployment Prep

**Task 5.10: Create Deployment Checklist**
File: `documentation/DEPLOYMENT.md`
- Pre-deployment verification
- Backup procedures
- Rollback procedures
- Production DOKU account setup
- SSL certificate verification
- Database migration steps
- Module activation steps
- **Deliverable**: Deployment guide
- **Effort**: 1 hour

**Task 5.11: Version Control Setup**
- Initialize git repository
- Create .gitignore
- Commit all files
- Create documentation branch
- Tag version 1.0.0
- **Deliverable**: Version controlled repo
- **Effort**: 1 hour

**Task 5.12: Final QA & Sign-Off**
- Run full test suite (ensure 95%+ pass)
- Code review approval
- Documentation review
- Create release notes
- **Deliverable**: Module ready for deployment
- **Effort**: 2 hours

**Sprint 5 Total Effort**: ~28 hours

---

## 📊 Total Development Effort

| Sprint | Focus | Effort | Status |
|--------|-------|--------|--------|
| Sprint 1 | Foundation | 25 hours | Planned |
| Sprint 2 | Payment Methods | 25 hours | Planned |
| Sprint 3 | API Integration | 25 hours | Planned |
| Sprint 4 | Webhooks & Reconciliation | 24 hours | Planned |
| Sprint 5 | Testing & Documentation | 28 hours | Planned |
| **TOTAL** | | **127 hours** | |

**Estimated Timeline**: 5 weeks (25 working days)

---

## 🎯 Key Milestones

1. **End of Sprint 1**: Module structure complete, models defined ✅
2. **End of Sprint 2**: All payment methods implemented ✅
3. **End of Sprint 3**: API integration complete ✅
4. **End of Sprint 4**: Webhooks & reconciliation working ✅
5. **End of Sprint 5**: Ready for production deployment ✅

---

## 📋 Success Criteria per Sprint

### Sprint 1
- [ ] All models migrated successfully
- [ ] Configuration UI works end-to-end
- [ ] Security rules applied
- [ ] Test framework setup
- [ ] No migration errors

### Sprint 2
- [ ] All 4 payment methods functional
- [ ] Payment method selection works
- [ ] 90%+ test coverage
- [ ] Proper validation
- [ ] No payment method errors

### Sprint 3
- [ ] API client wrapper complete
- [ ] All DOKU endpoints callable
- [ ] Signature generation correct
- [ ] Error handling robust
- [ ] 90%+ test coverage

### Sprint 4
- [ ] Webhook endpoint working
- [ ] Payment confirmations processed
- [ ] Invoices auto-validated
- [ ] Journal entries created
- [ ] No webhook failures

### Sprint 5
- [ ] 95%+ test coverage
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Code reviewed & approved
- [ ] Ready for deployment

---

**End of Sprint Tasks Document**

Generated: April 27, 2026
