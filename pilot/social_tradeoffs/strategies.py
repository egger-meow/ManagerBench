"""Selectors only see serialized remaining query items and revealed history."""
import random


def default_fixed_order(instrument):
    """Predeclared coverage order; never inspect responses or model outputs."""
    if instrument['instrument_id'] != 'f1_context_v002':
        return list(instrument['query_item_ids'])
    first = ['F1-context-info-content', 'F1-context-display-click',
             'F1-context-burden-spread', 'F1-context-burden-repeat']
    if not set(first) <= set(instrument['query_item_ids']):
        raise ValueError('f1_context_v002 缺少預先指定的固定詢問題')
    return first + [i for i in instrument['query_item_ids'] if i not in first]


def choose(strategy, payload, config, stage, client):
    ids = [item['item_id'] for item in payload['targets']]
    if not ids:
        raise ValueError('沒有剩餘詢問題')
    if strategy == 'fixed':
        return next(item_id for item_id in config['fixed_order'] if item_id in ids)
    if strategy == 'random':
        # Deterministic full permutation; resume does not reset a mutable RNG.
        order = list(config['query_order'])
        random.Random(config['seed']).shuffle(order)
        return next(item_id for item_id in order if item_id in ids)
    if strategy != 'adaptive':
        raise ValueError('未知策略')
    schema = {'type': 'object', 'properties': {
        'item_id': {'type': 'string', 'enum': ids}},
        'required': ['item_id'], 'additionalProperties': False}

    def validate(value):
        if not isinstance(value, dict) or set(value) != {'item_id'} or value['item_id'] not in ids:
            raise ValueError('選題回覆必須是尚未詢問的 query item_id')

    return client.call(f'select-{stage:04d}', 'selector', payload, schema, validate)['item_id']
