"""Same stateless predictor for every selection strategy; no answer-book access."""


def contract(targets):
    options = {}
    properties = {}
    for item in targets:
        item_id = item['item_id']
        response = item['response']
        fields = {field: response['accept_a_and_b_values' if field.startswith('accept_') else 'choice_values']
                  for field in ('accept_a', 'accept_b', 'choice')}
        options[item_id] = fields
        properties[item_id] = {
            'type': 'object',
            'properties': {field: {'type': ['string', 'null'], 'enum': values + [None]}
                           for field, values in fields.items()},
            'required': list(fields), 'additionalProperties': False,
        }
    schema = {'type': 'object', 'properties': properties,
              'required': list(properties), 'additionalProperties': False}

    def validate(value):
        if not isinstance(value, dict) or set(value) != set(options):
            raise ValueError('預測必須完整列出固定測試 ID，不能漏題或加題')
        for item_id, fields in options.items():
            prediction = value[item_id]
            if not isinstance(prediction, dict) or set(prediction) != set(fields):
                raise ValueError('預測欄位不一致')
            for field, values in fields.items():
                answer = prediction[field]
                if answer is not None and (not isinstance(answer, str) or answer not in values):
                    raise ValueError('預測選項無效')
    return schema, validate


def predict(payload, stage, client):
    schema, validate = contract(payload['targets'])
    return client.call(f'predict-{stage:04d}', 'predictor', payload, schema, validate)
