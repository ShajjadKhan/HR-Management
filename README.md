# Multi-Tenant HR Management SaaS for Contracting Companies

A multi-tenant Software-as-a-Service (SaaS) HR & Manpower Management solution designed for contracting companies, manpower suppliers, and facility management firms.

---

## 🌟 SaaS Architecture Overview

```
                          ┌────────────────────────┐
                          │      MASTER ADMIN      │
                          │   (SaaS Vendor/Owner)  │
                          └───────────┬────────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           │ Onboards / Grants Access │ Manages Subscriptions    │
           ▼                          ▼                          ▼
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  Al-Madina Co. (CR)  │   │  Gulf Apex Co. (CR)  │   │  Client Co. #3 (CR)  │
│  Tenant #1 (Max: 50) │   │  Tenant #2 (Max: 25) │   │  Tenant #3 (Max: 100)│
├──────────────────────┤   ├──────────────────────┤   ├──────────────────────┤
│ • Workers & Iqamas   │   │ • Workers & Iqamas   │   │ • Workers & Iqamas   │
│ • Camps & Housing    │   │ • Camps & Housing    │   │ • Camps & Housing    │
│ • Leaves & Holidays  │   │ • Leaves & Holidays  │   │ • Leaves & Holidays  │
│ • Payroll & History  │   │ • Payroll & History  │   │ • Payroll & History  │
│ • Reports (Excel)    │   │ • Reports (Excel)    │   │ • Reports (Excel)    │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘
   (Complete Data Isolation: No company can see another company's records)
```

### 1. Master Admin (SaaS Platform Owner)
- **Role**: Software Owner / Vendor.
- **Master Admin Portal (`/master-admin/`)**:
  - Global overview: Total contracting companies, active vs suspended licenses, total workers managed.
  - **Onboard New Contracting Companies**: Define company name, CR number, contact info, subscription plan, max worker quota, and expiry date. Automatically provisions company admin login credentials.
  - **Instant Access Control Toggle**: 1-click button to **Activate** or **Suspend** any contracting company's access (e.g. if contract payment is overdue).
  - **Quota Allocation**: Limit how many workers a contracting company can register based on their subscription tier (Starter, Standard, Enterprise).
  - **Live Company Impersonation**: Jump into any client company's HR dashboard with 1 click to view their setup or assist them, with an option to return back to Master Portal at any time.
  - **Password Reset**: Reset credentials for any company admin account.

### 2. Company Admin (Tenant - Contracting Company)
- **Role**: Administrator of the contracting company who bought the software.
- **Company Portal (`/`)**:
  - Real-time dashboard with quota utilization progress bar (`15 / 50 workers used`).
  - **Workers & Contractors Directory**: Manage workers, Iqama numbers, passports, sponsor (Kafeel), client project assignments, basic salaries, receiving contract amounts, and photos.
  - **Iqama Expiry & Visa Renewal Tracker**: Color-coded countdown alert for expiring or expired Iqamas.
  - **Housing & Accommodations**: Track camps/rooms and assign workers to accommodations.
  - **Leave Management**: Leave policies (Saudi Labor Law 21 days standard), balances, requests, and approvals.
  - **Monthly Salary Payment Tracker**: Interactive Jan-Dec payment buttons to mark monthly disbursement and log payment history.
  - **Excel Export**: Export complete worker directories and financial breakdowns filtered strictly to their company.
  - **Strict Data Isolation**: Automatic database scoping ensures no client company can ever access or modify another company's data.

---

## 🔑 Demo & Test Credentials

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **👑 Master Admin** | `master_admin` | `Admin@12345` | Full platform control & company management |
| **🏢 Company 1 Admin** | `almadina_admin` | `Madina@12345` | Al-Madina Contracting LLC (Quota: 50) |
| **🏢 Company 2 Admin** | `gulfapex_admin` | `Apex@12345` | Gulf Apex Manpower Co. (Quota: 25) |

---

## 🚀 How to Run the Application

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Run system check & automated test suite
python manage.py test employees

# 3. Start development server
python manage.py runserver 0.0.0.0:8000
```

Open your browser at:
- **Login Portal**: `http://127.0.0.1:8000/login/`
- **Master Admin Portal**: `http://127.0.0.1:8000/master-admin/`
- **Django Core Admin**: `http://127.0.0.1:8000/admin/`

---

## 🛡️ Tenant Access Enforcement

If a company's `is_active` status is switched off by the Master Admin or their `subscription_expiry` date has passed:
- Company users attempting to log in will receive an **Access Suspended** page.
- Direct API / URL access is immediately blocked.
- Master Admin can re-enable access with 1 click from the Master Portal once payment is received.
