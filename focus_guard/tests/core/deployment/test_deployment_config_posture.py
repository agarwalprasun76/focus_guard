from __future__ import annotations

import json

from focus_guard.deployment.config import DeploymentConfig


def test_load_backward_compatible_when_posture_fields_missing(tmp_path) -> None:
    config_path = tmp_path / "deployment_config.json"
    config_path.write_text(
        json.dumps(
            {
                "machine_name": "legacy-machine",
                "user_name": "legacy-user",
                "enforcement_mode": "enforcing",
                "run_as_service": True,
            }
        ),
        encoding="utf-8",
    )

    cfg = DeploymentConfig.load(config_path)

    assert cfg.machine_name == "legacy-machine"
    assert cfg.user_name == "legacy-user"
    assert cfg.deployment_posture_model == "admin_install_designated_monitored_user"
    assert cfg.installer_account_name == ""
    assert cfg.monitored_user_name == ""
    assert cfg.session_scope == "single_interactive_session"


def test_save_and_reload_persists_posture_fields(tmp_path) -> None:
    config_path = tmp_path / "deployment_config.json"
    cfg = DeploymentConfig(
        machine_name="test-box",
        user_name="child1",
        installer_account_name="admin1",
        monitored_user_name="child1",
        deployment_posture_model="admin_install_designated_monitored_user",
        session_scope="single_interactive_session",
    )

    assert cfg.save(config_path) is True
    loaded = DeploymentConfig.load(config_path)

    assert loaded.installer_account_name == "admin1"
    assert loaded.monitored_user_name == "child1"
    assert loaded.deployment_posture_model == "admin_install_designated_monitored_user"
    assert loaded.session_scope == "single_interactive_session"
