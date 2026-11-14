"""테스트 공통 설정"""

import pytest

from app import store


@pytest.fixture(autouse=True)
def already_promised(request, monkeypatch):
    """대부분의 테스트는 '처음 접속 때 약속(동의)을 마친 학생'에서 시작합니다.

    약속 화면 자체를 시험하는 테스트는 @pytest.mark.first_visit 를 붙여 이 기본값을 끕니다.
    """
    if request.node.get_closest_marker("first_visit"):
        return
    original = store.initial_state
    monkeypatch.setattr(store, "initial_state", lambda today: {
        **original(today), "consent": {"basic": True, "chat": True, "date": today, "time": "09:00"}})


def pytest_configure(config):
    config.addinivalue_line("markers", "first_visit: 약속(동의)을 아직 하지 않은 첫 방문 상태에서 시작")
