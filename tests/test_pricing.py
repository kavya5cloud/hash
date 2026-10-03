from hash_market.pricing import calculate_cost, get_model_pricing


MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"


def test_unknown_pricing_returns_none():
    assert calculate_cost(
        model="unknown/model",
        prompt_tokens=1000,
        completion_tokens=500,
    ) is None


def test_configured_model_calculates_cost():
    assert calculate_cost(
        model=MODEL,
        prompt_tokens=1000,
        completion_tokens=500,
    ) == 0.00018


def test_get_model_pricing_returns_configured_rates():
    input_rate, output_rate = get_model_pricing(MODEL)

    assert input_rate == 0.06
    assert output_rate == 0.24
