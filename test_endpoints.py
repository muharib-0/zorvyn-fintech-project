"""
Integration test script for all Finance Dashboard endpoints.
Writes results to test_results.log in UTF-8.
Run with: .\venv\Scripts\python test_endpoints.py
"""
import json
import sys
import requests

BASE = 'http://127.0.0.1:8000'
LOG_FILE = 'test_results.log'
results = []
passed = 0
failed = 0


def log(msg):
    results.append(msg)
    print(msg)


def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        log(f'  PASS: {name} (status={actual})')
        passed += 1
    else:
        log(f'  FAIL: {name} (expected={expected}, got={actual})')
        failed += 1


# ---- TESTS ----

log('Finance Dashboard API - Integration Tests')
log('=' * 60)

# 1. Login
log('\n[1] Login as admin')
r = requests.post(f'{BASE}/api/auth/login/', json={'username': 'admin', 'password': 'admin123'})
check('Login', r.status_code, 200)
data = r.json()
token = data['access']
role = data['role']
username = data['username']
log(f'  User: {username} ({role})')
headers = {'Authorization': f'Bearer {token}'}

# 2. Me
log('\n[2] GET /api/auth/me/')
r = requests.get(f'{BASE}/api/auth/me/', headers=headers)
check('Me endpoint', r.status_code, 200)

# 3. Create users
log('\n[3] Create viewer user')
r = requests.post(f'{BASE}/api/users/', headers=headers, json={
    'username': 'viewer1', 'email': 'viewer1@test.com',
    'password': 'viewer12345', 'role': 'VIEWER',
})
check('Create viewer', r.status_code, 201)

log('\n[4] Create analyst user')
r = requests.post(f'{BASE}/api/users/', headers=headers, json={
    'username': 'analyst1', 'email': 'analyst1@test.com',
    'password': 'analyst12345', 'role': 'ANALYST',
})
check('Create analyst', r.status_code, 201)

# 5. List users
log('\n[5] List all users')
r = requests.get(f'{BASE}/api/users/', headers=headers)
check('List users', r.status_code, 200)
log(f'  Users count: {len(r.json()["results"])}')

# 6. Viewer cannot access admin endpoints
log('\n[6] Viewer permission checks')
vr = requests.post(f'{BASE}/api/auth/login/', json={'username': 'viewer1', 'password': 'viewer12345'})
vtoken = vr.json()['access']
vheaders = {'Authorization': f'Bearer {vtoken}'}

r = requests.get(f'{BASE}/api/users/', headers=vheaders)
check('Viewer denied user list', r.status_code, 403)

# 7. Create records as admin
log('\n[7] Create financial records')
records_data = [
    {'amount': '5000.00', 'record_type': 'INCOME', 'category': 'CLIENT_REVENUE', 'date': '2025-01-15', 'notes': 'Jan client'},
    {'amount': '3500.00', 'record_type': 'INCOME', 'category': 'CONSULTING', 'date': '2025-02-15', 'notes': 'Feb consulting'},
    {'amount': '1200.00', 'record_type': 'EXPENSE', 'category': 'OFFICE_RENT', 'date': '2025-01-01', 'notes': 'Jan rent'},
    {'amount': '800.00', 'record_type': 'EXPENSE', 'category': 'OFFICE_RENT', 'date': '2025-02-01', 'notes': 'Feb rent'},
    {'amount': '150.00', 'record_type': 'EXPENSE', 'category': 'FOOD_BEVERAGES', 'date': '2025-01-10', 'notes': 'Client lunch'},
    {'amount': '2000.00', 'record_type': 'INCOME', 'category': 'PRODUCT_SALES', 'date': '2025-01-20', 'notes': 'License'},
    {'amount': '300.00', 'record_type': 'EXPENSE', 'category': 'UTILITIES_INTERNET', 'date': '2025-01-05', 'notes': 'Electric'},
    {'amount': '500.00', 'record_type': 'EXPENSE', 'category': 'TRAVEL_TRANSPORT', 'date': '2025-02-10', 'notes': 'Flight'},
    {'amount': '1000.00', 'record_type': 'INCOME', 'category': 'INVESTMENT_FUNDING', 'date': '2025-03-01', 'notes': 'Seed intro'},
    {'amount': '250.00', 'record_type': 'EXPENSE', 'category': 'SOFTWARE_TOOLS', 'date': '2025-03-05', 'notes': 'AWS bill'},
]
for rd in records_data:
    r = requests.post(f'{BASE}/api/records/', headers=headers, json=rd)
    check(f'Create {rd["record_type"]} {rd["category"]}', r.status_code, 201)

# 8. List records
log('\n[8] List records')
r = requests.get(f'{BASE}/api/records/', headers=headers)
check('List records', r.status_code, 200)
log(f'  Records count: {r.json()["count"]}')

# 9. Filter records
log('\n[9] Filter records by type')
r = requests.get(f'{BASE}/api/records/?record_type=INCOME', headers=headers)
check('Filter INCOME', r.status_code, 200)
log(f'  Income records: {r.json()["count"]}')

log('\n[10] Filter records by date range')
r = requests.get(f'{BASE}/api/records/?date_after=2025-01-01&date_before=2025-01-31', headers=headers)
check('Filter date range', r.status_code, 200)
log(f'  Jan 2025 records: {r.json()["count"]}')

# 10. Get single record
log('\n[11] Get single record')
r = requests.get(f'{BASE}/api/records/', headers=headers)
first_id = r.json()['results'][0]['id']
r = requests.get(f'{BASE}/api/records/{first_id}/', headers=headers)
check('Get record detail', r.status_code, 200)

# 11. Update record
log('\n[12] Update record')
r = requests.patch(f'{BASE}/api/records/{first_id}/', headers=headers, json={'notes': 'UPDATED note'})
check('Update record', r.status_code, 200)

# 12. Soft delete
log('\n[13] Soft delete record')
r = requests.get(f'{BASE}/api/records/', headers=headers)
last_id = r.json()['results'][-1]['id']
r = requests.delete(f'{BASE}/api/records/{last_id}/', headers=headers)
check('Soft delete', r.status_code, 200)

r = requests.get(f'{BASE}/api/records/', headers=headers)
log(f'  Records after delete: {r.json()["count"]} (should be 9)')

# 13. Viewer cannot create records
log('\n[14] Viewer cannot create records')
r = requests.post(f'{BASE}/api/records/', headers=vheaders, json={
    'amount': '100.00', 'record_type': 'EXPENSE', 'category': 'SALARIES', 'date': '2025-01-01'
})
check('Viewer denied create', r.status_code, 403)

# 14. Viewer CANNOT read records (Rubric update: Analyst+ only)
log('\n[15] Viewer CANNOT read records')
r = requests.get(f'{BASE}/api/records/', headers=vheaders)
check('Viewer denied records list', r.status_code, 403)

# 15. Dashboard summary
log('\n[16] Dashboard summary')
r = requests.get(f'{BASE}/api/dashboard/summary/', headers=headers)
check('Dashboard summary', r.status_code, 200)
summary = r.json()
log(f'  Income: {summary["total_income"]}, Expense: {summary["total_expense"]}, Balance: {summary["net_balance"]}')

# 16. Category totals
log('\n[17] Category totals')
r = requests.get(f'{BASE}/api/dashboard/category-totals/', headers=headers)
check('Category totals', r.status_code, 200)
log(f'  Categories: {len(r.json())}')

# 17. Monthly trends (admin)
log('\n[18] Monthly trends (admin)')
r = requests.get(f'{BASE}/api/dashboard/monthly-trends/', headers=headers)
check('Monthly trends admin', r.status_code, 200)
log(f'  Trend entries: {len(r.json())}')

# 18. Monthly trends (analyst)
log('\n[19] Monthly trends (analyst)')
ar = requests.post(f'{BASE}/api/auth/login/', json={'username': 'analyst1', 'password': 'analyst12345'})
atoken = ar.json()['access']
aheaders = {'Authorization': f'Bearer {atoken}'}
r = requests.get(f'{BASE}/api/dashboard/monthly-trends/', headers=aheaders)
check('Monthly trends analyst', r.status_code, 200)

# 19. Monthly trends (viewer → denied)
log('\n[20] Monthly trends (viewer - DENIED)')
r = requests.get(f'{BASE}/api/dashboard/monthly-trends/', headers=vheaders)
check('Viewer denied trends', r.status_code, 403)

# 20. Recent transactions
log('\n[21] Recent transactions')
r = requests.get(f'{BASE}/api/dashboard/recent/?count=5', headers=headers)
check('Recent transactions', r.status_code, 200)
log(f'  Recent count: {len(r.json())}')

# 21. Search records by notes keyword
log('\n[22] Search records by keyword')
r = requests.get(f'{BASE}/api/records/?search=client', headers=headers)
check('Search records (notes match)', r.status_code, 200)
client_count = r.json()['count']
log(f'  Records matching "client": {client_count}')

# 22. Future-date validation — date > 1 year ahead must be rejected
log('\n[23] Future-date validation')
r = requests.post(f'{BASE}/api/records/', headers=headers, json={
    'amount': '100.00', 'record_type': 'EXPENSE',
    'category': 'SALARIES', 'date': '2099-01-01',
})
check('Future date rejected (400)', r.status_code, 400)
log(f'  Error detail: {r.json().get("details", {})}')

# 23. Monthly trends includes month_label field
log('\n[24] Monthly trends includes month_label')
r = requests.get(f'{BASE}/api/dashboard/monthly-trends/', headers=headers)
check('Monthly trends 200', r.status_code, 200)
trends = r.json()
if trends:
    has_label = 'month_label' in trends[0]
    if has_label:
        log(f'  PASS: month_label present (e.g. "{trends[0]["month_label"]}")')
        passed += 1
    else:
        log('  FAIL: month_label missing from response')
        failed += 1
else:
    log('  SKIP: no trend data to check')

# 24. New Pandas Analytics Endpoints
log('\n[25] Pandas Analytics Endpoints (Viewer+ and Analyst+)')

r = requests.get(f'{BASE}/api/dashboard/cost-center-breakdown/', headers=headers)
check('Cost Center Breakdown', r.status_code, 200)

r = requests.get(f'{BASE}/api/dashboard/revenue-breakdown/', headers=vheaders)
check('Revenue Breakdown (Viewer)', r.status_code, 200)

r = requests.get(f'{BASE}/api/dashboard/people-cost-ratio/', headers=headers)
check('People Cost Ratio', r.status_code, 200)

r = requests.get(f'{BASE}/api/dashboard/burn-rate/', headers=vheaders)
check('Burn Rate (Viewer)', r.status_code, 200)

r = requests.get(f'{BASE}/api/dashboard/runway/', headers=vheaders)
check('Runway (Viewer)', r.status_code, 200)

r = requests.get(f'{BASE}/api/dashboard/mom-change/', headers=headers)
check('MoM Change (Analyst+)', r.status_code, 200)

r = requests.get(f'{BASE}/api/dashboard/cost-center-breakdown/', headers=vheaders)
check('Viewer denied Cost Center', r.status_code, 403)

# Summary
log('\n' + '=' * 60)
log(f'RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests')
log('=' * 60)

# Write to file
with open(LOG_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

if failed > 0:
    sys.exit(1)
