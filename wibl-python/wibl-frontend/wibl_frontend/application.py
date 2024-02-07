from typing import NoReturn

from wibl_frontend.app_globals import app, db


with app.app_context():
    db.create_all()


def main() -> NoReturn:
    app.run(debug=True)


if __name__ == "__main__":
    main()
