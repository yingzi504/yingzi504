import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.services import access_service as service
from app.main import app
from test_access_control import context


@pytest.mark.parametrize('name', ['testuser', '测试用户', 'someone@company.com'])
def test_named_account_initial_password(context, name):
    sessions, _ = context
    with sessions() as db:
        service.create_user(db, name)
    client = TestClient(app)
    assert client.post('/api/v1/auth/login', json={'email':name, 'password':'wrong'}).status_code == 401
    result = client.post('/api/v1/auth/login', json={'email':name, 'password':'123456'})
    assert result.status_code == 200
    assert result.json()['data']['role'] == 'member'
    assert client.post('/api/v1/auth/login', json={'email':'unregistered', 'password':'wrong'}).status_code == 401


def test_blank_account_is_rejected():
    with pytest.raises(HTTPException):
        service.normalize_email('   ')
