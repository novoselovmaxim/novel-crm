---
phase: import-company-review
reviewed: 2026-05-24T12:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - backend/app/models.py
  - backend/app/schemas.py
  - backend/app/routers/import_routes.py
  - backend/app/routers/companies.py
  - frontend/src/components/CompanyCard.tsx
  - frontend/src/components/CompanyTable.tsx
  - frontend/src/components/ImportModal.tsx
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
status: issues_found
---

# Code Review Report

**Reviewed:** 2026-05-24T12:00:00Z  
**Depth:** standard  
**Files Reviewed:** 7  
**Status:** issues_found

## Summary

Reviewed the complete import system (backend routes, frontend wizard) plus inline editing and source filtering. The import merge logic correctly fills only NULL fields. The PATCH endpoint properly creates audit log entries for every field change. Overall architecture is sound, but three medium-impact bugs were found: a UUID type mismatch that breaks the source filter, a lost original filename in import records, and a silent error-swallowing pattern in inline editing. Several minor issues and code quality improvements are also noted.

---

## Warnings

### WR-01: UUID string not converted in source filter — filter silently returns no results (or crashes)

**File:** `backend/app/routers/companies.py:76`  
**Issue:** The `source` query parameter is typed as `Optional[str]`, but `ImportSourceData.source_id` is a PostgreSQL `UUID(as_uuid=True)` column. Passing a raw string to SQLAlchemy filter produces `WHERE source_id = 'uuid-string'` without a cast. Depending on the asyncpg/SQLAlchemy version, this either crashes with a type error or silently returns zero rows because the UUID column rejects string comparison.

```python
# Line 75-78 — current code:
if source:
    subq = select(ImportSourceData.company_id).where(
        ImportSourceData.source_id == source,  # source is a str, column is UUID
        ImportSourceData.company_id.isnot(None)
    )
```

Same bug exists for the `assigned_to` filter on line 72-73 (`Company.assigned_to == assigned_to` where `assigned_to` is also `str`).

**Fix:** Convert the string to `uuid.UUID` before passing to the query:

```python
if source:
    source_uuid = uuid.UUID(source)  # raises ValueError if malformed; FastAPI will return 422
    subq = select(ImportSourceData.company_id).where(
        ImportSourceData.source_id == source_uuid,
        ImportSourceData.company_id.isnot(None)
    )
```

Similarly for `assigned_to` (line 72):
```python
if assigned_to:
    assigned_uuid = uuid.UUID(assigned_to)
    query = query.where(Company.assigned_to == assigned_uuid)
    count_query = count_query.where(Company.assigned_to == assigned_uuid)
```

### WR-02: Original filename lost during import — stored as generated UUID name

**File:** `backend/app/routers/import_routes.py:274-275`  
**Issue:** The `_run_import` function sets `original_filename` to a generated string `f"import_{req.file_id}{file_path.suffix}"` instead of the user's actual filename. The original filename is available in the `upload_file` endpoint but is never passed through to the import execution. As a result, the "Данные из источников" section in CompanyCard shows filenames like `import_uuid.xlsx` instead of the meaningful original name like `companies_2024.xlsx`.

```python
source = ImportSource(
    original_filename=f"import_{req.file_id}{file_path.suffix}",  # ← lost original name
    ...
)
```

**Fix:** Store the original filename during upload and pass it to `_run_import`. The cleanest approach: store it in a side table or add an `original_filename` field to the run request schema. Minimal fix:

Option A — Add `original_filename` to `ImportRunRequest` and have the frontend send it:

```python
class ImportRunRequest(BaseModel):
    file_id: str
    sheet: str
    mapping: dict[str, str]
    template_name: Optional[str] = None
    original_filename: Optional[str] = None  # <-- new field
```

Then in the upload endpoint's response, return the filename:

```python
return UploadPreview(
    file_id=file_id,
    original_filename=file.filename,  # <-- store for the frontend to pass back
    ...
)
```

And in `_run_import`:
```python
source = ImportSource(
    original_filename=req.original_filename or f"import_{req.file_id}{file_path.suffix}",
    ...
)
```

Option B — Store a mapping from file_id → original_filename in a dict or DB table during upload, retrieve in `_run_import`.

### WR-03: Silent error swallowing in inline field editor — data inconsistency on API failure

**File:** `frontend/src/components/CompanyCard.tsx:50`  
**Issue:** The `Field.save` function has an empty `catch {}` block. If the PATCH request fails (network error, 500, validation error), the user receives no feedback. The `onUpdate` callback is never called on error (it's after `await`), but the editing state is already closed (`setEditing(false)` on line 44 runs before the try). The user sees the field revert to its old value but has no indication the save failed. For a PATCH failure, this is confusing but recoverable. However, `handleFieldUpdate` could potentially be called in a way that creates inconsistency between local state and backend.

Related: line 397 in `ImportModal.tsx` and line 93 also have empty `catch {}` blocks for template operations.

```typescript
const save = async () => {
    if (!field || !companyId) return
    setEditing(false)
    if (editVal === (rawValue ?? value ?? '')) return
    if (editVal === '' && value === null) return
    try {
      await api.patch(`/companies/${companyId}`, { [field]: editVal || null })
      onUpdate?.(field, editVal)
    } catch { }  // ← silently swallows all errors
}
```

**Fix:** Show a toast or notification on failure. At minimum, rethrow for global error handlers:

```typescript
try {
    await api.patch(`/companies/${companyId}`, { [field]: editVal || null })
    onUpdate?.(field, editVal)
} catch (err) {
    console.error('Failed to save field', field, err)
    // Optional: show error toast. The value reverts since onUpdate wasn't called.
}
```

### WR-04: `list_sources` endpoint returns templates — source filter shows template entries

**File:** `backend/app/routers/import_routes.py:389-397`  
**Issue:** The `GET /import/sources` endpoint returns ALL `ImportSource` rows without filtering by status. Since templates are also stored as `ImportSource` entries (with `status="template"`), they appear in the frontend source filter dropdown. Filtering by a template's ID would always return 0 results (templates have no related `ImportSourceData`), confusing users.

```python
@router.get("/sources", response_model=list[ImportSourceResponse])
async def list_sources(...):
    result = await db.execute(
        select(ImportSource).order_by(ImportSource.uploaded_at.desc())
    )
    # Returns templates too!
```

**Fix:** Add a status filter:

```python
result = await db.execute(
    select(ImportSource)
    .where(ImportSource.status != "template")
    .order_by(ImportSource.uploaded_at.desc())
)
```

---

## Info

### IN-01: `from datetime import datetime` inside import loop (code smell)

**File:** `backend/app/routers/import_routes.py:323-324` and `352-353`  
**Issue:** `from datetime import datetime` is executed inside the `for idx, row in df.iterrows()` loop. Python caches imports, so this works, but it's confusing and suggests the import was added as an afterthought. For new companies (else branch) the import happens again.

**Fix:** Move to the top of the file (group with other stdlib imports).

### IN-02: `unusedFields` computed but never rendered

**File:** `frontend/src/components/ImportModal.tsx:118-121`  
**Issue:** The `unusedFields` variable is computed but never used in JSX. The logic also compares `f.key` (a DB field name like `"inn"`) against `Object.values(mapping)` (which are Excel column names like `"ИНН"`), making the filter semantically incorrect even if it were displayed.

**Fix:** Remove the dead code or fix and render it (e.g., show unmapped fields to the user).

### IN-03: `String(company.employees)` → `"null"` when employees is null

**File:** `frontend/src/components/CompanyCard.tsx:429`  
**Issue:** When `company.employees` is `null`, `String(null)` returns the string `"null"` (truthy), so the `|| ''` fallback never activates. Clicking to edit the employees field pre-fills the input with `"null"` instead of an empty string. Other number fields correctly use `company.revenue?.toString() || ''` (optional chaining returns `undefined` for null, triggering the fallback).

```tsx
rawValue={String(company.employees) || ''}  // Bug: String(null) = "null" (truthy)
// Should be:
rawValue={company.employees != null ? String(company.employees) : ''}
```

### IN-04: `handleFieldUpdate` uses `parseInt` without radix for number fields

**File:** `frontend/src/components/CompanyCard.tsx:163`  
**Issue:** `parseInt(val.replace(/\s/g, ''))` lacks a radix parameter. Modern ES5+ defaults to base 10, but for values like `"0123"` there's a theoretical octal interpretation risk in older environments. More importantly, `parseInt` truncates decimals silently (e.g., `"1500000.50"` → `1500000`), and for non-numeric strings returns `NaN` which gets stored in state.

**Fix:** Use `Number()` or add radix: `parseInt(val.replace(/\s/g, ''), 10)`, and validate the result:

```typescript
const parsed = NUM_FIELDS.has(field) 
    ? (val ? Number(val.replace(/\s/g, '')) || null : null) 
    : val
```

### IN-05: Auto-mapping false positive via substring match in translit slug

**File:** `backend/app/routers/import_routes.py:189-191`  
**Issue:** The transliteration fallback match checks `key in col_slug or col_slug in key`. Short keys like `"inn"` or `"size"` can match longer slugs as substrings. For example, `"inn"` is a substring of `"activity_main"` (at position 17), `"dinner"`, `"spinner"`, etc. While unlikely to trigger with Russian business Excel columns, this is a correctness issue.

**Fix:** Use exact match or word-boundary matching instead of substring:

```python
import re
# Check that the key appears as a whole word in the slug
if re.search(rf'\b{re.escape(key)}\b', col_slug):
    mapping[key] = col
    matched = True
    break
```

### IN-06: `selectedStatus` state not reverted on API error in status buttons

**File:** `frontend/src/components/CompanyCard.tsx:176-188`  
**Issue:** When a status button is clicked, `handleSaveCall(s.value)` is called. On API failure, the catch block only sets `saving = false`. The `selectedStatus` state remains at the new value, visually "sticking" the button to the new status even though the backend was not updated. A page reload fixes this, but the inconsistency persists until then.

**Fix:** Revert `selectedStatus` to `company.call_status` on error:

```typescript
try {
    await api.post(`/companies/${company.id}/call`, { ... })
    setNotes('')
    window.location.reload()
} catch {
    setSaving(false)
    setSelectedStatus(company.call_status)  // revert on failure
}
```

### IN-07: Frontend never sends `template_name` to `/import/run`

**File:** `frontend/src/components/ImportModal.tsx:104-109`  
**Issue:** The UI collects a `templateName` (line 182) with a "Сохранить" button that saves through the separate `/import/templates` endpoint. But the `runImport` payload (sent to `/import/run`) does not include `template_name`, even though the backend schema and route handler support it. This means the `template_name` field on the `ImportSource` record is always `None` for actual imports.

**Fix:** Include `template_name` in the run import payload:

```typescript
const { data } = await api.post<ImportResult>('/import/run', {
    file_id: preview.file_id,
    sheet,
    mapping,
    template_name: templateName || undefined,
})
```

---

## Additional Notes

- **Audit logging (PATCH):** Verified correct. Each field change in `update_company` creates an `AuditLog` entry with old/new values in the same transaction. All good.

- **Merge logic (NULL-only fill):** Verified correct. The `_run_import` function checks `getattr(company, field) is None` before setting values for strings, and `company.reg_date is None` / `getattr(company, field) is None` for dates and ints. Never overwrites existing values.

- **Route conflict check:** `GET /import/data` and `GET /import/sources/{source_id}/data` are structurally different paths under `/api/import/`. No conflict.

- **File cleanup:** The `finally` block in `run_import` correctly deletes the temp file. Uploaded files that are never consumed remain in `/tmp/import_uploads/` (potential disk growth, but low risk).

- **`formatNumericString` fragility:** The function uses `parseFloat` which stops at the first comma — `"1,500,000"` parses as `1`. If formatted number strings from Excel ever contain thousands separators, the table display will be wrong. However, with `dtype=str` in pandas, raw cell values are typically unformatted, so this is likely safe in practice.

---

_Reviewed: 2026-05-24T12:00:00Z_  
_Reviewer: gsd-code-reviewer_  
_Depth: standard_
