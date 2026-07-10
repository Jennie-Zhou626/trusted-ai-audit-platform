@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
python -c "import requests; API='http://127.0.0.1:8000/api'; requests.get(f'{API}/health', timeout=5).raise_for_status(); result=requests.post(f'{API}/samples/seed-sample', data={'reset':'true'}, timeout=30).json(); audits=requests.get(f'{API}/audits', timeout=5).json(); assert result['normal_audit']=='passed', result; assert result['tampered_audit']=='failed', result; assert len(audits)==2, audits; print(result)"
