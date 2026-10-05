"""Evaluator only; called AFTER all stage predictions are durably saved."""


def score(instrument, book, stages):
    truth = {item['item_id']: item['answer'] for item in book['items']}
    test_ids = instrument['test_item_ids']
    reports = []
    for stage, predictions in stages:
        fields = {}
        for field in ('accept_a', 'accept_b', 'choice'):
            available = sum(truth[i][field] is not None for i in test_ids)
            predicted = sum(truth[i][field] is not None and predictions[i][field] is not None for i in test_ids)
            correct = sum(truth[i][field] is not None and predictions[i][field] == truth[i][field] for i in test_ids)
            fields[field] = {
                'labels_available': available, 'missing_labels': len(test_ids) - available,
                'predictions_on_available_labels': predicted,
                'abstentions_all_test_items': sum(predictions[i][field] is None for i in test_ids),
                'coverage': predicted / available if available else None,
                'correct': correct, 'accuracy': correct / predicted if predicted else None,
            }
        reports.append({'stage': stage, 'fields': fields})
    return {'scoring_version': 'social-exact-v1', 'stages': reports,
            'note': 'reason 不評分；資訊不足、拒絕與不確定是有效類別；null 才是缺答／棄答'}
