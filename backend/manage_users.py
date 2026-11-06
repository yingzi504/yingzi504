"""Local-only administrator provisioning: python manage_users.py admin name@company.com."""
import argparse
import app.models
from app.models.database import SessionLocal
from app.services.access_service import create_user, audit


def main():
    parser = argparse.ArgumentParser(description="Create an administrator with initial password 123456")
    parser.add_argument("command", choices=["admin"])
    parser.add_argument("email", help="Administrator company email")
    args = parser.parse_args()
    with SessionLocal() as db:
        user = create_user(db, args.email, role="admin")
        audit("admin.bootstrap", resource_id=str(user.id), actor={"id": user.id})
    print("Administrator created. Initial password: 123456. Change it at first login.")


if __name__ == "__main__":
    main()
