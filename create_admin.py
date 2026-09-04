# create_admin.py
#
# Run this once to create your admin login:
#   python create_admin.py
#
# You can run it again later to add another admin account.

import getpass
import re
import db

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def main():
    db.init_db()

    print("Create an admin account for CoderSpot\n")

    email = input("Admin email: ").strip()
    if not EMAIL_PATTERN.match(email):
        print("That doesn't look like a valid email address. Try again.")
        return

    if db.get_admin_by_email(email):
        print(f"An admin account already exists for {email}.")
        return

    password = getpass.getpass("Admin password (min 8 characters): ")
    if len(password) < 8:
        print("Password must be at least 8 characters. Try again.")
        return

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords didn't match. Try again.")
        return

    db.create_admin(email, password)
    print(f"\nAdmin account created for {email}.")
    print("Log in at /admin/login once the app is running.")


if __name__ == "__main__":
    main()
