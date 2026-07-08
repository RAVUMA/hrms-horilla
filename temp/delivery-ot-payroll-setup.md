# Delivery Staff Overtime Payroll Setup — HJ Holdings

## Scenario

Delivery employees work a standard 10-hour day paid as a flat daily rate. Any
hours worked beyond 10 in a day are paid separately as overtime (OT), at a
per-hour OT rate, stacking on top of the flat day rate.

Example: 10 hrs worked = ₹1000 (day rate only). 12 hrs worked = ₹1000 (day
rate) + 2 hrs × ₹200 (OT rate) = ₹1400.

This is fully configurable through the Horilla admin UI — **no custom code
required**. It combines an Employee Shift (for the 10-hour threshold), a
Contract (with wage set to 0), and two Allowances (one flat per-day, one
per-OT-hour).

---

## Setup steps performed

### 1. Employee Shift
`Settings → Employee → Employee Shift`
- Name: **Delivery Shift**
- Weekly full time: `60:00` (assumes 6-day week — placeholder, confirm with
  client)
- Full time (monthly): `260:00` (placeholder, confirm with client)
- Company: HJ Holdings (pvt) ltd

### 2. Employee Shift Schedule (sets the 10-hour OT threshold)
`Settings → Employee → Employee Shift Schedule`
- Days: Monday–Sunday (all 7 — placeholder, confirm actual off-days with
  client)
- Shift: Delivery Shift
- **Minimum Working Hours: `10:00`** ← this is the core OT threshold. Any
  worked hours beyond this per day count as overtime.
- Start Time: `08:30 AM`, End Time: `07:30 PM` (placeholder window; adjust once
  real shift times are confirmed)
- **Enable Automatic Check Out: OFF** — must stay off, otherwise the system
  auto-clocks-out employees at End Time and cuts off any overtime worked past
  the shift window.

### 3. Work Type
`Settings → Employee → Work Type`
- Name: **Delivery**

### 4. Employee assignment
Employee profile → Edit → Work Info tab:
- Department: Delivery Dept
- Job Position: Driver (Delivery Dept)
- Shift: Delivery Shift
- Work Type: Delivery
- **Basic Salary: `0`**, **Salary Per Hour: `0`** — left at zero deliberately,
  since actual pay comes entirely from the Allowances below, not from this
  field or the Contract wage. Non-zero values here would risk double-paying
  the day rate.

### 5. Attendance overtime approval settings
`Settings → Attendance → Attendance Break Point` (this is the
`AttendanceValidationCondition` model — only one instance of this record can
ever exist)
- **Worked Hours (At Work) Auto Approve Till: `13:00`** — attendance days at or
  below this auto-validate without manual review; sets it above the normal
  10–12h range so routine OT days don't pile up needing manual approval.
- **Minimum Hour to Approve Overtime: `00:00`** — with Auto Approve OT
  enabled, any overtime amount (even a few minutes) auto-approves immediately.
- **Maximum Allowed Overtime Per Day: `06:00`** — a safety cap on daily OT.
  ⚠️ **Do not leave this as literal `00:00`** — see the bug note below.
- **Auto Approve OT: ✅ checked** — otherwise every day's overtime needs manual
  per-record approval before it counts toward pay.
- Company: HJ Holdings (pvt) ltd

### 6. Payroll Contract
`Payroll → Contract → Create`
- Employee: test_user (PEP01)
- Contract name: Delivery Contract
- Wage Type: Monthly
- **Wage: `0`** — deliberately zero; see note above.
- Pay Frequency: **Weekly** (business decision — how often HJ Holdings pays
  delivery staff)
- Department / Job Position / Shift / Work Type: matches employee's Work Info
- **Status: Active** ← critical. Payroll's payslip generation filters
  `contract_status="active"` in several places
  (`payroll/methods/methods.py`); a contract left in "Draft" is invisible to
  payroll entirely and no payslip will ever generate for that employee.

### 7. Allowance #1 — flat day rate
`Payroll → Allowances → Create`
- Title: **Delivery Day Rate**
- Is Fixed: OFF
- Based on: **Shift**
  - Shift: Delivery Shift
  - Shift per attendance amount: **`1000`**
- Specific Employees: test_user
- Has max limit: OFF

Calculation (`payroll/methods/payslip_calc.py`,
`calculate_based_on_shift`): counts validated attendance records on that shift
within the payslip period and multiplies by the per-attendance amount.

### 8. Allowance #2 — overtime hourly bonus
`Payroll → Allowances → Create`
- Title: **Delivery Overtime**
- Is Fixed: OFF
- Based on: **Overtime**
  - Amount per one hr: **`200`**
- Specific Employees: test_user
- Has max limit: OFF

Calculation (`calculate_based_on_overtime`): sums `overtime_second` across
attendance records with `attendance_overtime_approve=True` in the payslip
period, converts to hours, multiplies by the hourly rate.

These two allowances stack automatically into gross pay per payslip period.

---

## Test data created (July 1–7, 2026)

| Date | Clock In | Clock Out | Worked Hours | Expected OT |
|---|---|---|---|---|
| Jul 1 | 08:30 AM | 06:30 PM | 10h | 0 |
| Jul 2 | 08:30 AM | 06:30 PM | 10h | 0 |
| Jul 3 | 08:30 AM | 08:30 PM | 12h | 2h |
| Jul 4 | 08:30 AM | 06:30 PM | 10h | 0 |
| Jul 5 | 08:30 AM | 06:30 PM | 10h | 0 |
| Jul 6 | 08:30 AM | 06:30 PM | 10h | 0 |
| Jul 7 | 08:30 AM | 08:30 PM | 12h | 2h |

**Expected weekly payslip total:**
- 7 validated Delivery-shift days × ₹1000 = **₹7000**
- 4 approved OT hours (2 + 2) × ₹200 = **₹800**
- **Total: ₹7800**

---

## Bug encountered & fix: overtime showing 00:00 for all days

**Symptom**: Jul 3 and Jul 7 attendance records showed `Worked Hour: 12:00`,
`Min Hour: 10:00`, but `Overtime: 00:00` — should have been `02:00`.

**Root cause**: `attendance/models.py::handle_overtime_conditions()` applies a
hard cap:
```python
if condition.overtime_cutoff:
    cutoff_seconds = strtime_seconds(condition.overtime_cutoff)
    if self.overtime_second > cutoff_seconds:
        self.overtime_second = cutoff_seconds
        ...
```
`overtime_cutoff` is a `CharField` — an empty string is falsy (no cap), but a
literal `"00:00"` is a **truthy non-empty string**, so `cutoff_seconds`
evaluates to `0` and **all overtime gets capped to zero**. The "Maximum
Allowed Overtime Per Day" field on the Attendance Break Point form had
defaulted/been saved as literal `00:00` instead of being left blank.

**Fix applied**:
1. Edited the Attendance Break Point condition, changed "Maximum Allowed
   Overtime Per Day" from `00:00` to `06:00` (a real, generous daily cap
   instead of an accidental zero-cap).
2. Re-saved (opened edit, clicked Save with no changes) the affected
   attendance records — the overtime calculation is cached at save-time per
   record, so fixing the condition alone does not retroactively recalculate
   already-saved attendance rows. Each affected row must be re-saved once the
   condition is corrected.

**Takeaway for future setup**: never leave "Maximum Allowed Overtime Per Day"
as `00:00` — either leave it genuinely blank, or set a real cap value.

---

## Still to confirm with client
- Actual delivery shift work days per week (currently placeholder: all 7
  days)
- Actual shift start/end times (currently placeholder: 08:30 AM–07:30 PM)
- Actual pay frequency (currently set to Weekly)
- Whether a lunch break should be excluded from worked hours

## Open items / not yet verified
- Full payslip generation for July 1–7 has not yet been run to confirm the
  ₹7800 expected total matches the actual generated payslip.
