import printguard.mqtt as mqtt_module


class FakePahoClient:
    def __init__(self) -> None:
        self.tls_kwargs: dict[str, object] | None = None
        self.tls_insecure: bool | None = None
        self.logger = None

    def username_pw_set(self, username: str, password: str | None = None) -> None:
        self.username = username
        self.password = password

    def tls_set(self, **kwargs) -> None:
        self.tls_kwargs = kwargs

    def tls_insecure_set(self, value: bool) -> None:
        self.tls_insecure = value

    def enable_logger(self, logger) -> None:
        self.logger = logger

    def reconnect_delay_set(self, min_delay: int, max_delay: int) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay


def test_mqtt_client_configures_tls_when_enabled(monkeypatch) -> None:
    fake_client = FakePahoClient()
    monkeypatch.setattr(mqtt_module.mqtt, "Client", lambda *args, **kwargs: fake_client)

    mqtt_module.MQTTClient(
        host="mqtt.local",
        port=8883,
        client_id="printguard",
        username="user",
        password="pass",
        qos=1,
        retry_delay_ms=1000,
        connect_timeout_seconds=30,
        connect_max_attempts=0,
        tls_enabled=True,
        tls_insecure=True,
        tls_ca_path="/etc/ssl/custom-ca.pem",
        tls_certfile="/etc/ssl/client.crt",
        tls_keyfile="/etc/ssl/client.key",
    )

    assert fake_client.tls_kwargs is not None
    assert fake_client.tls_kwargs["ca_certs"] == "/etc/ssl/custom-ca.pem"
    assert fake_client.tls_kwargs["certfile"] == "/etc/ssl/client.crt"
    assert fake_client.tls_kwargs["keyfile"] == "/etc/ssl/client.key"
    assert fake_client.tls_insecure is True
