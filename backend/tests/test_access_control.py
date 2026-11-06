import json
from pathlib import Path
from datetime import datetime, timedelta
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models.database import Base
from app.models.access import User, LoginSession, AuditEvent, Resource
from app.services import access_service as service
from app.api import access
from app.main import app


@pytest.fixture
def context(monkeypatch, tmp_path):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(service, 'SessionLocal', sessions)
    monkeypatch.setattr(access, 'SessionLocal', sessions)
    monkeypatch.setattr(service.settings, 'output_dir', str(tmp_path / 'output'))
    monkeypatch.setattr('app.api.resume.UPLOAD_DIR', str(tmp_path))
    monkeypatch.setattr('app.main.import_legacy_outputs', lambda: None)
    with sessions() as db:
        for email, role in [('admin@company.test', 'admin'), ('alice@company.test', 'member'), ('bob@company.test', 'member')]:
            service.create_user(db, email, role)
    yield sessions, tmp_path
    engine.dispose()


def signed_in(email, change=True):
    client = TestClient(app)
    result = client.post('/api/v1/auth/login', json={'email': email, 'password': '123456'})
    assert result.status_code == 200
    assert 'HttpOnly' in result.headers['set-cookie']
    if change:
        result = client.post('/api/v1/auth/password', json={'current_password': '123456', 'new_password': 'Changed-password-123'})
        assert result.status_code == 200
    return client


def test_authentication_password_sessions_and_csrf(context):
    sessions, _ = context
    client = TestClient(app)
    for path in ['/process', '/resume/fill/outputs', '/history/list', '/template/list', '/records', '/admin/users']:
        assert client.get('/api/v1'+path).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email':'admin@company.test','password':'wrong'}).status_code == 401
    client = signed_in('alice@company.test', change=False)
    assert client.get('/api/v1/process').status_code == 403
    assert client.post('/api/v1/auth/password', json={'current_password':'wrong','new_password':'Changed-password-123'}).status_code == 400
    assert client.post('/api/v1/auth/password', json={'current_password':'123456','new_password':'Changed-password-123'}).status_code == 200
    assert client.post('/api/v1/auth/logout', headers={'origin':'https://hostile.test'}).status_code == 403
    # LAN sharing keeps working when DHCP changes the server's private IPv4,
    # while origins on unapproved ports remain blocked.
    lan_headers = {'origin': 'http://10.2.20.77:5173'}
    lan_client = TestClient(app)
    assert lan_client.post(
        '/api/v1/auth/login',
        json={'email': 'alice@company.test', 'password': 'Changed-password-123'},
        headers=lan_headers,
    ).status_code == 200
    preflight = client.options('/api/v1/auth/login', headers={
        **lan_headers,
        'access-control-request-method': 'POST',
    })
    assert preflight.status_code == 200
    assert preflight.headers['access-control-allow-origin'] == lan_headers['origin']
    assert client.post(
        '/api/v1/auth/login',
        json={'email': 'alice@company.test', 'password': '123456'},
        headers={'origin': 'http://10.2.20.77:9000'},
    ).status_code == 403
    assert lan_client.post('/api/v1/auth/logout', headers=lan_headers).status_code == 200
    assert client.get('/api/v1/auth/me').status_code == 200
    with sessions() as db:
        user = db.query(User).filter_by(email='alice@company.test').one()
        assert user.password_hash != '123456'
        assert service.password_matches('Changed-password-123',user.password_hash)
        session = db.query(LoginSession).filter_by(user_id=user.id).one()
        assert session.token_hash != client.cookies.get(access.COOKIE)
        session.expires_at = datetime.utcnow()-timedelta(seconds=1)
        db.commit()
    assert client.get('/api/v1/auth/me').status_code == 401


def test_ownership_task_archive_download_and_audit(context, monkeypatch):
    sessions, tmp = context
    alice, bob, admin = [signed_in(email+'@company.test') for email in ['alice','bob','admin']]
    uploaded = alice.post('/api/v1/resume/upload', files={'file':('cv.docx', b'test-document')})
    assert uploaded.status_code == 200
    file_id = uploaded.json()['data']['file_id']
    monkeypatch.setattr('app.api.process.PipelineService.start_pipeline', lambda task_id: None)
    payload={'file_id':file_id,'target_language':'CN','template_type':'vertical','department':'TD','job_position':'系统工程师'}
    assert bob.post('/api/v1/process', json=payload).status_code == 404
    result = alice.post('/api/v1/process', json=payload)
    assert result.status_code == 200, result.text
    tid = result.json()['data']['task_id']
    assert bob.get('/api/v1/process/'+tid).status_code == 404
    assert bob.post(f'/api/v1/process/{tid}/gender', json={'gender':'female'}).status_code == 404
    assert all(t['task_id'] != tid for t in bob.get('/api/v1/process').json()['tasks'])
    source=tmp/'output'/'shared.pptx';source.parent.mkdir();source.write_bytes(b'original output')
    task=SimpleNamespace(task_id=tid,status='completed',output_path=str(source),to_status_dict=lambda:{'task_id':tid,'status':'completed'})
    service.persist_task(task,'cv')
    source.write_bytes(b'later output')
    assert alice.get(f'/api/v1/process/{tid}/download?format=pptx').content == b'original output'
    assert alice.get(f'/api/v1/records/{tid}/download?format=pptx').content == b'original output'
    assert admin.get(f'/api/v1/records/{tid}/download?format=pptx').content == b'original output'
    assert bob.get(f'/api/v1/records/{tid}/download?format=pptx').status_code == 404
    assert bob.get(f'/api/v1/records/{tid}').status_code == 404
    assert alice.get(f'/api/v1/records/{tid}/download?format=pdf').status_code == 404
    assert bob.get('/api/v1/records').json()['total'] == 0
    assert alice.get('/api/v1/records').json()['total'] == 1
    library = alice.get('/api/v1/cv-library').json()
    assert library['total'] == 1
    assert library['data'][0]['department'] == 'TD'
    assert library['data'][0]['position'] == '系统工程师'
    assert alice.get('/api/v1/cv-library', params={'department': 'TD', 'position': '系统'}).json()['total'] == 1
    assert alice.get('/api/v1/cv-library', params={'department': 'HR'}).json()['total'] == 0
    assert bob.get('/api/v1/cv-library').json()['total'] == 0
    assert bob.get('/api/v1/resume/fill/download/shared.pptx').status_code == 403
    assert bob.get('/api/v1/admin/audit').status_code == 403
    events=admin.get('/api/v1/admin/audit').json()['data']
    assert any(e['resource_id']==tid and 'download' in e['action'] for e in events)
    assert any(e['action']=='cv.task.completed' for e in events)
    serialized=json.dumps(events)
    assert 'Changed-password' not in serialized and 'resume_session' not in serialized
    # Metadata and archived files remain available independent of the in-memory task.
    assert admin.get(f'/api/v1/records/{tid}').json()['data']['metadata']['status']=='completed'


def test_cv_department_is_required_and_uses_fixed_directory(context, monkeypatch):
    alice = signed_in('alice@company.test')
    uploaded = alice.post('/api/v1/resume/upload', files={'file':('cv.docx', b'test-document')})
    file_id = uploaded.json()['data']['file_id']
    monkeypatch.setattr('app.api.process.PipelineService.start_pipeline', lambda task_id: None)
    base = {'file_id': file_id, 'target_language': 'CN', 'template_type': 'vertical'}
    assert alice.post('/api/v1/process', json=base).status_code == 422
    assert alice.post('/api/v1/process', json=dict(base, department='Engineering')).status_code == 422
    assert alice.post('/api/v1/process', json=dict(base, department='TV-X1')).status_code == 200
    assert alice.get('/api/v1/cv-library', params={'department': 'Engineering'}).status_code == 422


def test_admin_permissions_disable_reset_and_throttling(context):
    sessions,_=context
    admin=signed_in('admin@company.test');alice=signed_in('alice@company.test')
    users=admin.get('/api/v1/admin/users').json()['data'];uid=next(u['id'] for u in users if u['email']=='alice@company.test')
    body={'active':True,'account_type':'limited','permissions':['jd']}
    assert admin.put(f'/api/v1/admin/users/{uid}',json=body).status_code==200
    assert alice.get('/api/v1/process').status_code==403
    assert alice.get('/api/v1/jd/list').status_code==403
    assert alice.post('/api/v1/admin/users',json={'email':'other@company.test'}).status_code==403
    assert admin.post('/api/v1/admin/users',json={'email':'new@company.test','permissions':['cv']}).status_code==200
    assert admin.post('/api/v1/admin/users',json={'email':'NEW@company.test'}).status_code==409
    assert admin.post(f'/api/v1/admin/users/{uid}/reset-password').status_code==200
    assert alice.get('/api/v1/auth/me').status_code==401
    alice=signed_in('alice@company.test',change=False)
    assert alice.get('/api/v1/records').status_code==403
    body['active']=False
    assert admin.put(f'/api/v1/admin/users/{uid}',json=body).status_code==200
    assert alice.get('/api/v1/auth/me').status_code==401
    with sessions() as db:
        for _ in range(10):
            db.add(AuditEvent(action='auth.login.failed',status_code=401,ip_address='testclient'))
        db.commit()
    assert TestClient(app).post('/api/v1/auth/login',json={'email':'bob@company.test','password':'123456'}).status_code==429


def test_legacy_files_admin_only_and_path_boundary(context):
    sessions,tmp=context
    root=tmp/'output';root.mkdir();(root/'old.pptx').write_bytes(b'legacy')
    service.import_legacy_outputs();service.import_legacy_outputs()
    admin=signed_in('admin@company.test');alice=signed_in('alice@company.test')
    records=admin.get('/api/v1/records').json()['data'];assert len(records)==1
    rid=records[0]['id']
    assert admin.get(f'/api/v1/records/{rid}/download?format=pptx').content==b'legacy'
    assert alice.get('/api/v1/records').json()['total']==0
    assert alice.get(f'/api/v1/records/{rid}/download?format=pptx').status_code==404
    outside=tmp/'private.docx';outside.write_bytes(b'private')
    with sessions() as db:
        item=db.get(Resource,rid);item.files=json.dumps({'docx':str(outside)});db.commit()
    assert admin.get(f'/api/v1/records/{rid}/download?format=docx').status_code==404


def test_jd_task_archive_and_restart_state(context, monkeypatch):
    sessions, tmp = context
    alice = signed_in('alice@company.test')
    bob = signed_in('bob@company.test')
    monkeypatch.setattr('app.api.jd_conversion.JDConversionService.start_task', lambda task_id: None)
    result = alice.post('/api/v1/jd-conversion/tasks', json={'target_position': 'Engineer', 'target_position_source': 'manual'})
    assert result.status_code == 200, result.text
    tid = result.json()['data']['task_id']
    assert bob.get(f'/api/v1/jd-conversion/tasks/{tid}').status_code == 404
    assert bob.post(f'/api/v1/jd-conversion/tasks/{tid}/location', json={'location':'Shanghai'}).status_code == 404
    output = tmp/'output'; output.mkdir()
    docx = output/'JD.docx'; pdf = output/'JD.pdf'
    docx.write_bytes(b'JD document'); pdf.write_bytes(b'JD pdf')
    task = SimpleNamespace(task_id=tid, status='completed', docx_path=str(docx), pdf_path=str(pdf),
                           status_dict=lambda:{'task_id':tid,'status':'completed'})
    service.persist_task(task,'jd')
    for extension, content in [('docx',b'JD document'),('pdf',b'JD pdf')]:
        assert alice.get(f'/api/v1/jd-conversion/tasks/{tid}/download?format={extension}').content == content
        assert bob.get(f'/api/v1/records/{tid}/download?format={extension}').status_code == 404
    with sessions() as db:
        db.add(Resource(id='interrupted-task',owner_id=2,kind='cv',status='awaiting_input'))
        db.commit()
    service.import_legacy_outputs()
    with sessions() as db:
        assert db.get(Resource,'interrupted-task').status == 'interrupted'
        assert db.get(Resource,tid).status == 'completed'
        assert db.query(Resource).filter_by(kind='legacy').count() == 0
    assert alice.get(f'/api/v1/records/{tid}/download?format=docx').content == b'JD document'
