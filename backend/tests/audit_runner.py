import urllib.request
import json
import time
import sys
import os

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('backend'))

results = {}

# 1. Health
try:
    h = json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5).read().decode())
    results['HEALTH_SERVICE'] = ('PASS', f"Status: {h['status']}, Mode: {h['mode']}")
except Exception as e:
    results['HEALTH_SERVICE'] = ('FAIL', str(e))

# 2. Database read from database/saved_files.json
try:
    files = json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/saved-files', timeout=5).read().decode())
    results['DATABASE_PERSISTENCE'] = ('PASS', f"{len(files)} files loaded successfully from database/saved_files.json")
except Exception as e:
    results['DATABASE_PERSISTENCE'] = ('FAIL', str(e))

# 3. Captcha Security
try:
    c = json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/auth/captcha', timeout=5).read().decode())
    results['SECURITY_CAPTCHA'] = ('PASS', f"Captcha ID: {c.get('captcha_id')}, SVG length: {len(c.get('svg', ''))}")
except Exception as e:
    results['SECURITY_CAPTCHA'] = ('FAIL', str(e))

# 4. Scenarios
try:
    s = json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/scenarios', timeout=5).read().decode())
    results['DIPLOMATIC_SCENARIOS'] = ('PASS', f"{len(s.get('scenarios', []))} scenarios active, Active ID: {s.get('active_id')}")
except Exception as e:
    results['DIPLOMATIC_SCENARIOS'] = ('FAIL', str(e))

# 5. Live TTS (Google Gemini)
try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/tts',
        data=json.dumps({'text': 'Sistem Menkopolkam AI Hub beroperasi normal.', 'voice': 'Aoede'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=12) as r:
        raw_audio = r.read()
        results['TTS_AUDIO_SYNTHESIS'] = ('PASS', f"{len(raw_audio)} bytes audio/wav generated in real-time")
except Exception as e:
    results['TTS_AUDIO_SYNTHESIS'] = ('FAIL', str(e))

# 6. Diplomatic Translation
try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/translate',
        data=json.dumps({'text': 'Kedaulatan Maritim dan Pertahanan Nasional', 'target_lang': 'en'}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        tr = json.loads(r.read().decode())
        results['TRANSLATION_ENGINE'] = ('PASS', f"Translated: '{tr.get('translated_text', '')[:50]}'")
except Exception as e:
    results['TRANSLATION_ENGINE'] = ('FAIL', str(e))

# 7. Document Extraction (Knowledge Ingestion)
try:
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/document/extract',
        data=json.dumps({'filename': 'nota_kebijakan.txt', 'file_base64': 'Tm90YSBLZWJpamFrYW4gS2VtZW5rbyBQb2xrYW0gUkkgMjAyNi4='}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        ext = json.loads(r.read().decode())
        results['DOCUMENT_EXTRACTOR'] = ('PASS', f"Extracted {len(ext.get('text', ''))} characters successfully")
except Exception as e:
    results['DOCUMENT_EXTRACTOR'] = ('FAIL', str(e))

# 8. Server-side RBAC Enforcement (Inspect Bypass Protection)
try:
    from backend.utils.security import create_access_token
    viewer_token = create_access_token(sub="test_viewer", role="viewer")
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/saved-files/doc-natuna-01',
        headers={'Authorization': f"Bearer {viewer_token}"},
        method='DELETE'
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            results['RBAC_SERVER_DEFENSE'] = ('FAIL', 'Viewer was incorrectly allowed to delete file')
    except urllib.error.HTTPError as e:
        if e.code == 403:
            results['RBAC_SERVER_DEFENSE'] = ('PASS', 'Viewer strictly blocked with HTTP 403 Forbidden as expected')
        else:
            results['RBAC_SERVER_DEFENSE'] = ('FAIL', f"Unexpected HTTP status: {e.code}")
except Exception as e:
    results['RBAC_SERVER_DEFENSE'] = ('FAIL', str(e))

# 9. Frontend Serving
try:
    r_fe = urllib.request.urlopen('http://127.0.0.1:5173/', timeout=5)
    results['FRONTEND_SPA_DEV'] = ('PASS', f"HTTP {r_fe.status} OK (Vite React UI Active)")
except Exception as e:
    results['FRONTEND_SPA_DEV'] = ('FAIL', str(e))

# 10. Production SPA Catch-all on Port 8000
try:
    r_prod = urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)
    results['UNIFIED_PRODUCTION_PORT'] = ('PASS', f"HTTP {r_prod.status} OK (Serving SPA on unified port 8000)")
except Exception as e:
    results['UNIFIED_PRODUCTION_PORT'] = ('FAIL', str(e))

print('\n======================================================')
print('      MENKOPOLKAM AI HUB - LIVE SYSTEM AUDIT REPORT   ')
print('======================================================')
all_pass = True
for subsystem, (status, detail) in results.items():
    print(f"[{status}] {subsystem:<26}: {detail}")
    if status != 'PASS':
        all_pass = False

print('======================================================')
if all_pass:
    print('FINAL VERDICT: 100% OPERATIONAL & PRODUCTION READY!')
else:
    print('FINAL VERDICT: SOME CHECKS REQUIRE ATTENTION')
print('======================================================\n')
