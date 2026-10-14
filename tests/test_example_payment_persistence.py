import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest


TOOLS_ROOT = Path(__file__).resolve().parents[1] / 'examples'


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_tool(monkeypatch, environment, name):
    folder = TOOLS_ROOT / environment / 'input' / 'tools'
    util = _load_module(folder / 'util.py', f'{environment}_payment_util')
    with monkeypatch.context() as patch:
        patch.setitem(sys.modules, 'util', util)
        module = _load_module(folder / f'{name}.py', f'{environment}_{name}')
    return module, util


def _users(payment_methods):
    return pd.DataFrame([
        {
            'user_id': 'user_1',
            'name': 'Traveler',
            'payment_methods': json.dumps(payment_methods),
            'reservations': '[]',
        },
        {
            'user_id': 'user_2',
            'name': 'Other traveler',
            'payment_methods': '{}',
            'reservations': '[]',
        },
    ])


@pytest.fixture
def airline(monkeypatch):
    module, util = _load_tool(monkeypatch, 'airline', 'book_reservation')
    data = {
        'users': _users({
            'gift_card_1': {'source': 'gift_card', 'amount': 100},
            'certificate_1': {'source': 'certificate', 'amount': 40},
        }),
        'flights': pd.DataFrame([{
            'flight_number': 'HAT001',
            'origin': 'SFO',
            'destination': 'JFK',
            'dates': json.dumps({
                '2024-05-20': {
                    'status': 'available',
                    'available_seats': {'economy': 10},
                    'prices': {'economy': 40},
                },
            }),
        }]),
    }
    return module.BookReservation, util, data


def _book(tool, data, payment_id='gift_card_1', amount=40):
    return tool.invoke(
        data=data,
        user_id='user_1',
        origin='SFO',
        destination='JFK',
        flight_type='one_way',
        cabin='economy',
        flights=[{'flight_number': 'HAT001', 'date': '2024-05-20'}],
        passengers=[{'first_name': 'Test', 'last_name': 'Traveler',
                     'dob': '1990-01-01'}],
        payment_methods=[{'payment_id': payment_id, 'amount': amount}],
        total_baggages=0,
        nonfree_baggages=0,
        insurance='no',
    )


@pytest.mark.parametrize('payment_id', ['gift_card_1', 'certificate_1'])
def test_booking_persists_payment_and_reservation(airline, payment_id):
    tool, util, data = airline
    other_user = data['users'].iloc[1].copy()

    reservation = json.loads(_book(tool, data, payment_id))
    user = util.get_dict_json(data['users'], 'user_id')['user_1']

    if payment_id == 'gift_card_1':
        assert user['payment_methods'][payment_id]['amount'] == 60
    else:
        assert payment_id not in user['payment_methods']
    assert user['reservations'] == [reservation['reservation_id']]
    assert user['name'] == 'Traveler'
    pd.testing.assert_series_equal(data['users'].iloc[1], other_user)


def test_later_booking_cannot_reuse_spent_gift_card_balance(airline):
    tool, util, data = airline

    first = json.loads(_book(tool, data))
    second = json.loads(_book(tool, data))
    assert _book(tool, data) == 'Error: not enough balance in payment method gift_card_1'

    user = util.get_dict_json(data['users'], 'user_id')['user_1']
    assert user['payment_methods']['gift_card_1']['amount'] == 20
    assert user['reservations'] == [first['reservation_id'], second['reservation_id']]
    assert len(data['reservations']) == 2


@pytest.mark.parametrize('amount', [101, 39])
def test_rejected_booking_leaves_user_unchanged(airline, amount):
    tool, _, data = airline
    before = data['users'].copy(deep=True)

    assert _book(tool, data, amount=amount).startswith('Error:')

    pd.testing.assert_frame_equal(data['users'], before)
    assert 'reservations' not in data


@pytest.fixture
def retail(monkeypatch):
    module, util = _load_tool(monkeypatch, 'retail', 'modify_pending_order_payment')
    data = {
        'users': _users({
            'credit_card_1': {'source': 'credit_card', 'balance': 100},
            'gift_card_1': {'source': 'gift_card', 'balance': 100},
            'gift_card_2': {'source': 'gift_card', 'balance': 100},
            'gift_card_low': {'source': 'gift_card', 'balance': 30},
        }),
        'orders': pd.DataFrame([{
            'order_id': '#ORDER1',
            'user_id': 'user_1',
            'status': 'pending',
            'payment_history': json.dumps([{
                'transaction_type': 'payment',
                'amount': 40,
                'method': 'credit_card_1',
            }]),
        }]),
    }
    return module.ModifyPendingOrderPayment, util, data


@pytest.mark.parametrize('old_id,new_id,expected', [
    ('credit_card_1', 'gift_card_1', {'gift_card_1': 60}),
    ('gift_card_1', 'credit_card_1', {'gift_card_1': 140}),
    ('gift_card_1', 'gift_card_2', {'gift_card_1': 140, 'gift_card_2': 60}),
])
def test_payment_change_persists_debit_and_refund(retail, old_id, new_id, expected):
    tool, util, data = retail
    other_user = data['users'].iloc[1].copy()
    history = [{'transaction_type': 'payment', 'amount': 40, 'method': old_id}]
    data['orders'].loc[0, 'payment_history'] = json.dumps(history)

    result = json.loads(tool.invoke(data, '#ORDER1', new_id))

    user = util.get_dict_json(data['users'], 'user_id')['user_1']
    for payment_id, balance in expected.items():
        assert user['payment_methods'][payment_id]['balance'] == balance
    assert user['payment_methods']['credit_card_1']['balance'] == 100
    assert user['name'] == 'Traveler'
    assert util.get_dict_json(data['orders'], 'order_id')['#ORDER1'] == result
    pd.testing.assert_series_equal(data['users'].iloc[1], other_user)


def test_rejected_payment_change_leaves_user_and_order_unchanged(retail):
    tool, _, data = retail
    users_before = data['users'].copy(deep=True)
    orders_before = data['orders'].copy(deep=True)

    result = tool.invoke(data, '#ORDER1', 'gift_card_low')

    assert result == 'Error: insufficient gift card balance to pay for the order'
    pd.testing.assert_frame_equal(data['users'], users_before)
    pd.testing.assert_frame_equal(data['orders'], orders_before)
