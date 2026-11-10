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
    assert alice.get(f'/api/v1/records/{tid}/download?format=pptx').headers['cache-control'] == 'no-store'
    assert admin.get(f'/api/v1/records/{tid}/download?format=pptx').content == b'original output'
    assert bob.get(f'/api/v1/records/{tid}/download?format=pptx').status_code == 404
    assert bob.get(f'/api/v1/records/{tid}').status_code == 404
    def unavailable(*args, **kwargs):
        raise FileNotFoundError('PDF converter unavailable in this fixture')
    monkeypatch.setattr('app.services.pdf_converter.PdfConverterService.ensure_pdf_for_pptx', unavailable)
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


def test_legacy_cv_pdf_download_generates_and_persists_pdf(context, monkeypatch):
    sessions, tmp = context
    admin = signed_in('admin@company.test')
    output = tmp / 'output'
    archive = output / 'archive' / 'legacy-cv'
    archive.mkdir(parents=True)
    pptx = archive / 'resume.pptx'
    pptx.write_bytes(b'PPTX fixture')
    pdf = archive / 'resume.pdf'

    with sessions() as db:
        db.add(Resource(
            id='legacy-cv', owner_id=1, kind='cv', status='completed',
            files=json.dumps({'pptx': str(pptx.resolve())}),
        ))
        db.commit()

    def fake_ensure(source, target_dir):
        assert source == str(pptx.resolve())
        assert target_dir == str(archive)
        pdf.write_bytes(b'%PDF generated fixture')
        return str(pdf.resolve())

    monkeypatch.setattr(
        'app.services.pdf_converter.PdfConverterService.ensure_pdf_for_pptx',
        fake_ensure,
    )
    response = admin.get('/api/v1/records/legacy-cv/download?format=pdf')
    assert response.status_code == 200
    assert response.content == b'%PDF generated fixture'
    with sessions() as db:
        assert json.loads(db.get(Resource, 'legacy-cv').files)['pdf'] == str(pdf.resolve())


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
    assert alice.get('/api/v1/auth/me').status_code==401
    alice=TestClient(app)
    assert alice.post('/api/v1/auth/login', json={'email':'alice@company.test','password':'Changed-password-123'}).status_code==200
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


def test_auth_version_invalidates_stale_session_even_if_session_row_remains(context):
    sessions, _ = context
    alice = signed_in('alice@company.test')
    with sessions() as db:
        user = db.query(User).filter_by(email='alice@company.test').one()
        session = db.query(LoginSession).filter_by(user_id=user.id).one()
        assert session.auth_version == user.auth_version
        user.auth_version += 1
        db.commit()
    assert alice.get('/api/v1/auth/me').status_code == 401


def test_superadmin_live_login_count_and_admin_grants(context):
    sessions, _ = context
    with sessions() as db:
        service.create_user(db, 'root@company.test', role='superadmin')
    root = signed_in('root@company.test')
    admin = signed_in('admin@company.test')
    bob = signed_in('bob@company.test')
    users = root.get('/api/v1/admin/users').json()['data']
    bob_id = next(user['id'] for user in users if user['email'] == 'bob@company.test')
    admin_id = next(user['id'] for user in users if user['email'] == 'admin@company.test')
    root_id = next(user['id'] for user in users if user['email'] == 'root@company.test')

    assert root.get('/api/v1/admin/statistics').json()['data']['logged_in_users'] == 3
    assert admin.get('/api/v1/admin/statistics').json()['data']['logged_in_users'] == 3
    assert admin.post('/api/v1/admin/users', json={'email': 'blocked-admin@company.test', 'role': 'admin'}).status_code == 403
    assert admin.post(f'/api/v1/superadmin/users/{bob_id}/grant-admin').status_code == 403
    assert admin.get('/api/v1/admin/tools/recruitment-config').status_code == 200
    assert bob.get('/api/v1/admin/tools/recruitment-config').status_code == 403
    calculation = admin.post('/api/v1/admin/tools/recruitment-calculate', json={'plans': [
        {'id': 1, 'isCurrent': True, 'city': 'SH', 'basePay': 18000, 'onsite': 0,
         'annualBonus': 54000, 'projectBonus': 0, 'benefits': 21600, 'supplementary': 0,
         'contributionMode': 'salary'},
        {'id': 2, 'isCurrent': False, 'city': 'SH', 'basePay': 20000, 'onsite': 0,
         'annualBonus': 0, 'projectBonus': 0, 'benefits': 5800, 'supplementary': 19200,
         'contributionMode': 'salary'},
    ]})
    assert calculation.status_code == 200
    calculated = calculation.json()['data']
    assert calculated['1']['totalPackage'] == 291600
    assert calculated['2']['annualBonus'] == 40000
    assert calculated['2']['totalPackage'] == 305000
    assert calculated['2']['increaseRate'] == 0.05
    assert calculated['2']['cities']['SH']['rates']['hourly'] > 0
    assert bob.post('/api/v1/admin/tools/recruitment-calculate', json={'plans': [{'id': 1}]}).status_code == 403
    assert root.post(f'/api/v1/superadmin/users/{bob_id}/grant-admin').status_code == 200
    assert bob.get('/api/v1/auth/me').status_code == 401

    # A promoted administrator must re-authenticate; ordinary admins cannot
    # edit or disable other administrator accounts.
    bob = TestClient(app)
    assert bob.post('/api/v1/auth/login', json={
        'email': 'bob@company.test', 'password': 'Changed-password-123'
    }).status_code == 200
    assert bob.get('/api/v1/admin/users').status_code == 403
    body = {'active': False, 'account_type': 'standard', 'permissions': []}
    assert admin.put(f'/api/v1/admin/users/{bob_id}', json=body).status_code == 403
    assert admin.post(f'/api/v1/admin/users/{bob_id}/reset-password').status_code == 403
    assert root.post(f'/api/v1/admin/users/{root_id}/reset-password').status_code == 403
    assert root.post('/api/v1/admin/users', json={'email': 'new-admin@company.test', 'role': 'admin'}).status_code == 200
    assert root.post(f'/api/v1/superadmin/users/{admin_id}/revoke-admin').status_code == 200
    assert admin.get('/api/v1/auth/me').status_code == 401
    with sessions() as db:
        assert db.get(User, admin_id).role == 'member'

    with sessions() as db:
        assert db.get(User, bob_id).role == 'admin'


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


def test_personal_audit_cannot_expand_scope_and_admin_can_classify(context):
    sessions, _ = context
    alice, bob, admin = [signed_in(name+'@company.test') for name in ('alice', 'bob', 'admin')]
    with sessions() as db:
        alice_id = db.query(User).filter_by(email='alice@company.test').one().id
        bob_id = db.query(User).filter_by(email='bob@company.test').one().id
    service.audit('cv.task.completed', resource_id='alice-task', actor={'id': alice_id}, ip='10.2.13.61')
    service.audit('jd.task.failed', 500, resource_id='bob-task', actor={'id': bob_id})
    response = alice.get('/api/v1/audit', params={'user_id': bob_id, 'action': '.task.'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] == 1
    assert payload['summary']['by_category'] == {'cv': 1}
    assert payload['data'][0]['resource_id'] == 'alice-task'
    assert 'ip_address' not in payload['data'][0]
    assert payload['data'][0]['actor_role'] == 'member'
    assert alice.get('/api/v1/admin/audit').status_code == 403
    assert bob.get('/api/v1/admin/statistics').status_code == 403
    payload = admin.get('/api/v1/admin/audit', params={'action': '.task.'}).json()
    assert payload['total'] == 2
    assert payload['summary']['success'] == 1 and payload['summary']['failed'] == 1
    assert next(item for item in payload['data'] if item['user_id'] == alice_id)['ip_address'] == '10.2.13.*'
    filtered = admin.get('/api/v1/admin/audit', params={'category': 'jd', 'result': 'failed', 'user_id': bob_id}).json()
    assert filtered['total'] == 1
    assert filtered['data'][0]['resource_id'] == 'bob-task'
    assert alice.get('/api/v1/audit', params={'category': 'not-real'}).status_code == 422
    assert alice.get('/api/v1/audit', params={'start': '2026-11-10T00:00:00Z', 'end': '2026-11-01T00:00:00Z'}).status_code == 422
    assert TestClient(app).get('/api/v1/audit').status_code == 401


def test_audit_snapshots_account_type_resource_department_and_utc_filters(context):
    sessions, _ = context
    admin = signed_in('admin@company.test')
    with sessions() as db:
        user = db.query(User).filter_by(email='alice@company.test').one()
        user.account_type = 'hr'
        uid = user.id
        db.add(Resource(id='owned-cv', owner_id=uid, kind='cv', department='TD', status='completed'))
        db.commit()
    service.audit('GET /api/v1/records/{resource_id}/download', resource_id='owned-cv', actor={'id': uid})
    with sessions() as db:
        event = db.query(AuditEvent).filter_by(resource_id='owned-cv').one()
        event.created_at = datetime(2026, 11, 9, 1, 0)
        db.get(User, uid).account_type = 'changed-later'
        db.commit()
    params = dict(category='file', resource_type='cv', department='TD', account_type='hr',
                  start='2026-11-09T08:30:00+08:00', end='2026-11-09T09:30:00+08:00')
    payload = admin.get('/api/v1/admin/audit', params=params).json()
    assert payload['total'] == 1
    assert payload['data'][0]['account_type'] == 'hr'
    assert payload['data'][0]['actor_role'] == 'member'
    assert payload['data'][0]['department'] == 'TD'
    assert payload['data'][0]['created_at'].endswith('Z')
    assert admin.get('/api/v1/admin/audit', params=dict(params, resource_id='other')).json()['total'] == 0


def test_historical_audit_backfill_is_idempotent_without_inventing_roles(context):
    sessions, _ = context
    with sessions() as db:
        db.add(AuditEvent(action='GET /api/v1/records/{resource_id}/download', status_code=404))
        db.add(AuditEvent(action='auth.login.failed', status_code=401))
        db.commit()
    service.backfill_audit_categories()
    service.backfill_audit_categories()
    with sessions() as db:
        rows = db.query(AuditEvent).order_by(AuditEvent.id).all()
        assert len(rows) == 2
        assert [row.category for row in rows] == ['file', 'auth']
        assert all(row.result == 'failed' and row.actor_role == '' and row.account_type == '' for row in rows)


def test_audit_migration_preserves_old_rows_and_is_idempotent(monkeypatch):
    from sqlalchemy import inspect
    from app.models import migrations
    engine = create_engine('sqlite://')
    with engine.begin() as connection:
        connection.exec_driver_sql('CREATE TABLE access_audit (id INTEGER PRIMARY KEY, action VARCHAR(120), status_code INTEGER)')
        connection.exec_driver_sql('CREATE TABLE access_users (id INTEGER PRIMARY KEY)')
        connection.exec_driver_sql('CREATE TABLE access_sessions (token_hash VARCHAR(64) PRIMARY KEY)')
        connection.exec_driver_sql("INSERT INTO access_audit VALUES (1, 'auth.login.failed', 401)")
    monkeypatch.setattr(migrations, 'engine', engine)
    migrations.ensure_runtime_columns()
    migrations.ensure_runtime_columns()
    assert set(migrations.ACCESS_AUDIT_COLUMNS).issubset({column['name'] for column in inspect(engine).get_columns('access_audit')})
    assert set(migrations.ACCESS_USER_COLUMNS).issubset({column['name'] for column in inspect(engine).get_columns('access_users')})
    assert set(migrations.ACCESS_SESSION_COLUMNS).issubset({column['name'] for column in inspect(engine).get_columns('access_sessions')})
    with engine.connect() as connection:
        assert connection.exec_driver_sql('SELECT id, action, status_code, category FROM access_audit').one() == (1, 'auth.login.failed', 401, '')
    engine.dispose()
