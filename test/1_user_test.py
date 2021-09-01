from time import sleep
import pytest
import logging


from penguin.app import app
from penguin.models import drop_tables, create_tables
from penguin.db import ranks

USER_EMAIL = "hsn6@tuta.io"
USER_NAME = "Hassan"


@pytest.fixture(scope="function")
def test_client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def init_db():
    assert drop_tables()
    assert create_tables()
    assert ranks.flushdb()


g = {}


@pytest.mark.incremental
class TestUser:
    def test_hello(self, test_client):
        resp = test_client.get("/v1/hello")

        status: int = resp.status_code

        assert status == 200
        assert b"hello" == resp.data

    def test_create_user(self, test_client):
        resp = test_client.post(
            "/v1/users", json={"email": USER_EMAIL, "name": USER_NAME}
        )
        j: dict = resp.get_json()
        status: int = resp.status_code

        assert status == 201
        assert "token" in j
        assert "referral_code" in j

        g["token"] = j["token"]
        g["referral_code"] = j["referral_code"]

    def test_create_users(self, test_client):
        referral_code = ""
        for i in range(10):
            sleep(1)
            resp = test_client.post(
                "/v1/users",
                json={
                    "email": str(i) + USER_EMAIL,
                    "name": str(i) + USER_NAME,
                    "referred_by__referral_code": referral_code,
                },
            )
            j: dict = resp.get_json()
            status: int = resp.status_code

            assert status == 201
            assert "token" in j
            assert "referral_code" in j

            if i % 2 == 0:
                referral_code = j["referral_code"]

    def test_show_user(self, test_client):
        resp = test_client.get("/v1/users/me?token=" + g["token"])

        j: dict = resp.get_json()
        status: int = resp.status_code

        logging.debug(j)

        assert status == 200
        assert "id" in j
