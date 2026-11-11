import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.access import User, AuditEvent
from app.api import access
from test_access_control import context


@pytest.mark.parametrize(('name', 'must_change_password'), [
    ('NewUser', True),
    ('新用户', True),
    ('new@company.test', False),
    ('QualityTeStAccount', False),
    ('admin', True),
])
def test_auto_signup_requires_password_change_except_test_accounts(context, name, must_change_password):
    sessions, _ = context
    client = TestClient(app)
    assert client.post('/api/v1/auth/login', json={'email':name,'password':'wrong'}).status_code == 401
    with sessions() as db:
        assert db.query(User).filter_by(email=name.lower()).first() is None
    result = client.post('/api/v1/auth/login', json={'email':name,'password':'123456'})
    assert result.status_code == 200
    user = result.json()['data']
    assert user['role'] == 'member'
    assert user['must_change_password'] is must_change_password
    assert client.get('/api/v1/process').status_code == (403 if must_change_password else 200)
    assert client.get('/api/v1/admin/users').status_code == 403
    second = client.post('/api/v1/auth/login', json={'email':' '+name+' ','password':'123456'})
    assert second.json()['data']['id'] == user['id']
    with sessions() as db:
        assert db.query(User).filter_by(email=name.lower()).count() == 1
        assert db.query(AuditEvent).filter_by(action='auth.account.created', user_id=user['id']).count() == 1


def test_existing_password_and_disabled_state_are_not_reset(context):
    sessions, _ = context
    client = TestClient(app)
    payload={'email':'newmember','password':'123456'}
    assert client.post('/api/v1/auth/login',json=payload).status_code == 200
    assert client.post('/api/v1/auth/password',json={'current_password':'123456','new_password':'Changed-1234'}).status_code == 200
    assert client.post('/api/v1/auth/login',json=payload).status_code == 401
    payload['password']='Changed-1234'
    assert client.post('/api/v1/auth/login',json=payload).status_code == 200
    with sessions() as db:
        user=db.query(User).filter_by(email='newmember').one()
        user.active=False
        db.commit()
    assert client.post('/api/v1/auth/login',json=payload).status_code == 401
    assert client.get('/api/v1/auth/me').status_code == 401


@pytest.mark.parametrize('environment', ['production', 'prod', ' PRODUCTION '])
def test_production_never_auto_creates_accounts(context, monkeypatch, environment):
    sessions, _ = context
    monkeypatch.setattr(access.settings, 'environment', environment)
    monkeypatch.setattr(access.settings, 'auto_signup_enabled', True)
    client = TestClient(app)
    result = client.post('/api/v1/auth/login', json={
        'email': 'unregistered-user', 'password': '123456'
    })
    assert result.status_code == 401
    with sessions() as db:
        assert db.query(User).filter_by(email='unregistered-user').first() is None


def test_auto_signup_can_be_disabled_outside_production(context, monkeypatch):
    sessions, _ = context
    monkeypatch.setattr(access.settings, 'environment', 'development')
    monkeypatch.setattr(access.settings, 'auto_signup_enabled', False)
    result = TestClient(app).post('/api/v1/auth/login', json={
        'email': 'disabled-bootstrap', 'password': '123456'
    })
    assert result.status_code == 401
    with sessions() as db:
        assert db.query(User).filter_by(email='disabled-bootstrap').first() is None
