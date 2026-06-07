from __future__ import annotations

from app.models.entities import AccountStatus, BilibiliAccount, MonitorTarget, RiskStatus, Tenant
from app.services import targets as target_service


def _seed_target_context(db_session):
    tenant = Tenant(name="Tenant Target", slug="tenant-target", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    account = BilibiliAccount(
        tenant_id=tenant.id,
        uid=30001,
        username="target-account",
        status=AccountStatus.active.value,
        risk_status=RiskStatus.normal.value,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return tenant, account


async def test_preview_import_candidates_marks_existing_targets(db_session, monkeypatch):
    tenant, account = _seed_target_context(db_session)
    existing = MonitorTarget(
        tenant_id=tenant.id,
        account_id=account.id,
        oid=111,
        bvid="BV1existing111",
        title="Existing Video",
        poll_interval=300,
        status="active",
    )
    db_session.add(existing)
    db_session.commit()

    async def fake_import_video_targets(_account):
        return [
            {"oid": 111, "bvid": "BV1existing111", "title": "Existing Video", "owner_mid": 1},
            {"oid": 222, "bvid": "BV1newvideo22", "title": "New Video", "owner_mid": 2},
        ]

    monkeypatch.setattr(target_service.gateway, "import_video_targets", fake_import_video_targets)

    candidates = await target_service.preview_import_candidates(db_session, tenant.id, account)

    assert len(candidates) == 2
    assert candidates[0].bvid == "BV1existing111"
    assert candidates[0].already_monitored is True
    assert candidates[1].bvid == "BV1newvideo22"
    assert candidates[1].already_monitored is False


async def test_import_selected_candidates_respects_selection_and_interval(db_session, monkeypatch):
    tenant, account = _seed_target_context(db_session)

    async def fake_import_video_targets(_account):
        return [
            {"oid": 111, "bvid": "BV1keep11111", "title": "Keep Video", "owner_mid": 1},
            {"oid": 222, "bvid": "BV1skip22222", "title": "Skip Video", "owner_mid": 2},
        ]

    monkeypatch.setattr(target_service.gateway, "import_video_targets", fake_import_video_targets)

    created = await target_service.import_selected_candidates(
        db_session,
        tenant.id,
        account,
        selected_bvids=["BV1keep11111"],
        only_missing=True,
        poll_interval=900,
    )

    assert len(created) == 1
    assert created[0].bvid == "BV1keep11111"
    assert created[0].poll_interval == 900


async def test_import_selected_candidates_skips_existing_when_only_missing(db_session, monkeypatch):
    tenant, account = _seed_target_context(db_session)
    existing = MonitorTarget(
        tenant_id=tenant.id,
        account_id=account.id,
        oid=111,
        bvid="BV1existing111",
        title="Existing Video",
        poll_interval=300,
        status="active",
    )
    db_session.add(existing)
    db_session.commit()

    async def fake_import_video_targets(_account):
        return [
            {"oid": 111, "bvid": "BV1existing111", "title": "Existing Video", "owner_mid": 1},
            {"oid": 333, "bvid": "BV1brandnew33", "title": "Brand New", "owner_mid": 3},
        ]

    monkeypatch.setattr(target_service.gateway, "import_video_targets", fake_import_video_targets)

    created = await target_service.import_selected_candidates(
        db_session,
        tenant.id,
        account,
        selected_bvids=None,
        only_missing=True,
        poll_interval=300,
    )

    assert len(created) == 1
    assert created[0].bvid == "BV1brandnew33"


async def test_import_selected_candidates_never_duplicates_existing_targets(db_session, monkeypatch):
    tenant, account = _seed_target_context(db_session)
    existing = MonitorTarget(
        tenant_id=tenant.id,
        account_id=account.id,
        oid=111,
        bvid="BV1existing111",
        title="Existing Video",
        poll_interval=300,
        status="active",
    )
    db_session.add(existing)
    db_session.commit()

    async def fake_import_video_targets(_account):
        return [
            {"oid": 111, "bvid": "BV1existing111", "title": "Existing Video", "owner_mid": 1},
            {"oid": 444, "bvid": "BV1fresh44444", "title": "Fresh Video", "owner_mid": 4},
        ]

    monkeypatch.setattr(target_service.gateway, "import_video_targets", fake_import_video_targets)

    created = await target_service.import_selected_candidates(
        db_session,
        tenant.id,
        account,
        selected_bvids=["BV1existing111", "BV1fresh44444"],
        only_missing=False,
        poll_interval=600,
    )

    assert len(created) == 1
    assert created[0].bvid == "BV1fresh44444"
