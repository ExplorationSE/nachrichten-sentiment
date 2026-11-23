from datetime import date, datetime, timezone

from nachrichten_sentiment.timeutil import (
    FIRST_BATCH_ID,
    FIRST_BERLIN_DAY,
    batch_id_from_datetime,
    berlin_day_from_batch_id,
    datetime_from_batch_id,
    expected_batch_ids_for_berlin_day,
    iter_batch_ids,
    next_batch_id,
    previous_berlin_day,
)


def test_first_batch_is_berlin_19_february_2015():
    assert FIRST_BATCH_ID == "20150218230000"
    assert FIRST_BERLIN_DAY == date(2015, 2, 19)
    assert berlin_day_from_batch_id(FIRST_BATCH_ID) == date(2015, 2, 19)
    assert datetime_from_batch_id(FIRST_BATCH_ID) == datetime(2015, 2, 18, 23, 0, 0, tzinfo=timezone.utc)


def test_expected_batches_regular_winter_day_has_96():
    ids = expected_batch_ids_for_berlin_day(date(2015, 2, 19))
    assert len(ids) == 96
    assert ids[0] == "20150218230000"
    assert ids[-1] == "20150219224500"
    assert berlin_day_from_batch_id(ids[-1]) == date(2015, 2, 19)
    assert berlin_day_from_batch_id(next_batch_id(ids[-1])) == date(2015, 2, 20)


def test_expected_batches_follow_european_dst():
    spring = expected_batch_ids_for_berlin_day(date(2026, 3, 29))  # 23-Stunden-Tag
    autumn = expected_batch_ids_for_berlin_day(date(2026, 10, 25))  # 25-Stunden-Tag
    assert len(spring) == 92
    assert len(autumn) == 100
    assert all(berlin_day_from_batch_id(i) == date(2026, 3, 29) for i in spring)
    assert all(berlin_day_from_batch_id(i) == date(2026, 10, 25) for i in autumn)


def test_iter_and_previous_day():
    ids = iter_batch_ids("20150218230000", "20150218233000")
    assert ids == ["20150218230000", "20150218231500", "20150218233000"]
    now = datetime(2026, 11, 22, 8, 0, tzinfo=timezone.utc)  # 09:00 Europe/Berlin
    assert previous_berlin_day(now) == date(2026, 11, 21)
    assert batch_id_from_datetime(datetime(2015, 2, 18, 23, 0, tzinfo=timezone.utc)) == "20150218230000"
