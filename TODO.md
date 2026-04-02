# TODO: Login System Enhancement

## Backend Changes
- [ ] 1. Modify RegisterView to allow self-registration (AllowAny permission)
- [ ] 2. Add OAuth views for Google and Apple
- [ ] 3. Add OAuth URLs to urls.py
- [ ] 4. Update settings.py for OAuth credentials

## Frontend Changes
- [ ] 5. Install @react-oauth/google package
- [ ] 6. Update api.js with OAuth endpoints
- [ ] 7. Update Login.jsx with Sign Up form and OAuth buttons
- [ ] 8. Test the complete flow

## Implementation Notes
- Self-registration creates users with 'analyst' role by default
- Google and Apple OAuth credentials should be added to settings
- OAuth flow: Frontend handles OAuth popup, sends token to backend for verification
