from hypothesis import given
from hypothesis import strategies as st

from app.services.flag_eval import stable_bucket


@given(tenant=st.text(min_size=1), flag=st.text(min_size=1), uid=st.text(min_size=1))
def test_bucket_stable(tenant, flag, uid):
    a = stable_bucket(tenant, flag, uid)
    b = stable_bucket(tenant, flag, uid)
    assert a == b
    assert 0.0 <= a < 1.0
