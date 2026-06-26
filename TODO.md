# TODO

## Mongo users_collection + User model fixes
- [ ] Replace global `from mongo_connection import users_collection` usage in `backend/accounts/models.py` with safe runtime getters to avoid None/connection-time issues.
- [ ] Fix `User.save()`/`update_last_login()` to correctly handle `_id` types (ObjectId vs string) and always persist `date_joined/last_login` safely.
- [ ] Fix `User.create_user()` so it passes a valid `password_hash` even when `password=None` (OAuth flows) and avoids crashing.
- [ ] Fix exception swallowing (`except:`) to narrow to `Exception` where safe (avoid masking real bugs), while keeping fallback behavior.
- [ ] Add unit test coverage or adjust existing tests to validate Mongo and file fallback behaviors.
- [ ] Run backend test suite to confirm everything passes.

## Progress log
- [x] (0/5) Inspect and plan done.
- [x] (1/5) Update `backend/accounts/models.py` implementation.
- [x] (2/5) Add/adjust tests for file fallback + password=None + _id normalization.
- [x] (3/5) Ensure tests can run when Mongo is unavailable.
- [x] (4/5) Run pytest suite.
- [x] (5/5) Fix any failures and re-run.


