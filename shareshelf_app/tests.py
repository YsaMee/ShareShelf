"""Tests for the Prolog rules in logic/rules.pl.

They run the real rules through SWI-Prolog but don't touch the database, so
`python manage.py test` works without DATABASE_URL being reachable.
"""

from datetime import date, timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase

from . import logic

TODAY = date(2026, 11, 4)


def item(pk=1, owner=10, listing='give', category='Stationery', condition='Gently Used', qty=1, paused=False):
    return SimpleNamespace(pk=pk, owner_id=owner, listing=listing, category=category,
                           condition=condition, qty=qty, paused=paused)


def request(pk=100, requester=20, category='Stationery', preference='Flexible', status='open',
            is_lend=False, return_by=None):
    return SimpleNamespace(pk=pk, requester_id=requester, category=category, preference=preference,
                           status=status, is_lend=is_lend, return_by=return_by)


class MatchingTests(SimpleTestCase):
    def test_same_category_from_someone_else_matches(self):
        self.assertEqual(logic.find_matches([item()], [request()]), [(100, 1)])

    def test_own_item_never_matches(self):
        self.assertFalse(logic.is_match(item(owner=20), request(requester=20)))

    def test_other_category_does_not_match(self):
        self.assertFalse(logic.is_match(item(category='Electronics'), request()))

    def test_paused_or_empty_items_do_not_match(self):
        self.assertFalse(logic.is_match(item(paused=True), request()))
        self.assertFalse(logic.is_match(item(qty=0), request()))

    def test_only_give_away_items_are_suggested(self):
        self.assertFalse(logic.is_match(item(listing='lend'), request()))

    def test_flexible_accepts_any_condition(self):
        for condition in ('New', 'Gently Used', 'Functional'):
            self.assertTrue(logic.is_match(item(condition=condition), request(preference='Flexible')))

    def test_a_condition_preference_needs_that_exact_condition(self):
        self.assertTrue(logic.is_match(item(condition='New'), request(preference='New')))
        self.assertFalse(logic.is_match(item(condition='Functional'), request(preference='New')))

    def test_one_query_covers_many_requests(self):
        items = [item(pk=1, category='Stationery'), item(pk=2, category='Electronics')]
        requests = [request(pk=100, category='Stationery'), request(pk=101, category='Electronics')]
        self.assertEqual(sorted(logic.find_matches(items, requests)), [(100, 1), (101, 2)])

    def test_text_with_quotes_is_passed_safely(self):
        tricky = "Drafting & Arts (Architecture, Fine Arts) - it's"
        self.assertTrue(logic.is_match(item(category=tricky), request(category=tricky)))


class LifecycleTests(SimpleTestCase):
    def test_accepting_sets_one_unit_aside(self):
        self.assertEqual(logic.allowed_qty(request(status='requested'), 'sharer', 'matched', item(qty=3)), 2)

    def test_cannot_accept_without_stock_or_while_paused(self):
        self.assertIsNone(logic.allowed_qty(request(status='requested'), 'sharer', 'matched', item(qty=0)))
        self.assertIsNone(logic.allowed_qty(request(status='requested'), 'sharer', 'matched', item(paused=True)))

    def test_only_the_sharer_accepts_or_declines(self):
        self.assertIsNone(logic.allowed_qty(request(status='requested'), 'seeker', 'matched', item()))
        self.assertIsNone(logic.allowed_qty(request(status='requested'), 'seeker', 'declined', item()))
        self.assertEqual(logic.allowed_qty(request(status='requested'), 'sharer', 'declined', item(qty=1)), 1)

    def test_give_away_ends_fulfilled_and_lending_ends_lent(self):
        give, lend = request(status='matched'), request(status='matched', is_lend=True)
        self.assertIsNotNone(logic.allowed_qty(give, 'seeker', 'fulfilled', item()))
        self.assertIsNone(logic.allowed_qty(give, 'seeker', 'lent', item()))
        self.assertIsNotNone(logic.allowed_qty(lend, 'sharer', 'lent', item()))
        self.assertIsNone(logic.allowed_qty(lend, 'sharer', 'fulfilled', item()))

    def test_returning_gives_the_unit_back_up_to_20(self):
        lent = request(status='lent', is_lend=True)
        self.assertEqual(logic.allowed_qty(lent, 'sharer', 'returned', item(qty=0)), 1)
        self.assertEqual(logic.allowed_qty(lent, 'sharer', 'returned', item(qty=20)), 20)
        self.assertIsNone(logic.allowed_qty(lent, 'seeker', 'returned', item(qty=0)))

    def test_cancelling_a_match_gives_the_unit_back(self):
        self.assertEqual(logic.allowed_qty(request(status='matched'), 'seeker', 'cancelled', item(qty=0)), 1)
        self.assertEqual(logic.allowed_qty(request(status='requested'), 'seeker', 'cancelled', item(qty=2)), 2)
        self.assertEqual(logic.allowed_qty(request(status='open'), 'seeker', 'cancelled'), 0)

    def test_loans_and_closed_requests_cannot_be_cancelled(self):
        for status in ('lent', 'fulfilled', 'returned', 'cancelled', 'declined'):
            self.assertIsNone(logic.allowed_qty(request(status=status, is_lend=True), 'seeker', 'cancelled', item()))

    def test_an_open_request_can_be_sent_to_a_sharer(self):
        self.assertEqual(logic.allowed_qty(request(status='open'), 'seeker', 'requested'), 0)


class BorrowingTests(SimpleTestCase):
    def test_good_dates_have_no_problems(self):
        self.assertEqual(logic.loan_problems(7, TODAY, TODAY + timedelta(days=7), TODAY), [])

    def test_start_in_the_past(self):
        self.assertIn('starts_in_past', logic.loan_problems(7, TODAY - timedelta(days=1), TODAY + timedelta(days=2), TODAY))

    def test_return_must_be_after_start(self):
        self.assertEqual(logic.loan_problems(7, TODAY, TODAY, TODAY), ['ends_before_start'])
        self.assertEqual(logic.loan_problems(7, TODAY + timedelta(days=3), TODAY + timedelta(days=1), TODAY),
                         ['ends_before_start'])

    def test_loan_longer_than_the_limit(self):
        self.assertEqual(logic.loan_problems(7, TODAY, TODAY + timedelta(days=8), TODAY), ['too_long'])

    def test_no_limit_means_any_length(self):
        self.assertEqual(logic.loan_problems(None, TODAY, TODAY + timedelta(days=90), TODAY), [])


class OverdueTests(SimpleTestCase):
    def test_only_loans_past_their_return_date_are_overdue(self):
        late = request(pk=1, status='lent', return_by=TODAY - timedelta(days=1))
        due_today = request(pk=2, status='lent', return_by=TODAY)
        later = request(pk=3, status='lent', return_by=TODAY + timedelta(days=3))
        self.assertEqual(logic.find_overdue([late, due_today, later], TODAY), {1})

    def test_nothing_on_loan_needs_no_prolog_call(self):
        self.assertEqual(logic.find_overdue([], TODAY), set())
