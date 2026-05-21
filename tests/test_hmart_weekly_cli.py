from lifesource.daily import hmart_weekly


def test_hmart_weekly_cli_runs_monitor(monkeypatch, capsys):
    def fake_monitor():
        return {"changed": True, "sent": True, "deals": 0}

    monkeypatch.setattr(hmart_weekly, "run_hmart_weekly_ad_monitor", fake_monitor)

    exit_code = hmart_weekly.main(["monitor"])

    assert exit_code == 0
    assert "changed=True" in capsys.readouterr().out


def test_hmart_weekly_cli_runs_digest(monkeypatch, capsys):
    def fake_digest():
        return {"changed": False, "sent": True, "deals": 0}

    monkeypatch.setattr(hmart_weekly, "run_hmart_weekly_planning_digest", fake_digest)

    exit_code = hmart_weekly.main(["digest"])

    assert exit_code == 0
    assert "sent=True" in capsys.readouterr().out
