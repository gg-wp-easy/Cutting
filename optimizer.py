"""Exact pattern model for unlimited stock lengths; one kerf per produced piece."""
import math
import time
from decimal import Decimal
import pulp


def optimize(stocks, lengths, counts, blade=0, angle=0, thickness=0):
    if not stocks or not lengths or len(lengths) != len(counts):
        raise ValueError('Введите исходные длины, длины деталей и их количества.')
    if len(lengths) > 100 or sum(counts) > 10000:
        raise ValueError('За один расчёт допустимо до 100 размеров и 10000 деталей.')
    if any(not math.isfinite(x) or x <= 0 for x in [*stocks, *lengths]):
        raise ValueError('Длины должны быть положительными числами.')
    if any(not isinstance(x, int) or x < 0 for x in counts) or not any(counts):
        raise ValueError('Количество должно быть целым неотрицательным числом; заказ не может быть пустым.')
    if not all(math.isfinite(x) for x in (blade, angle, thickness)) or blade < 0 or thickness < 0 or angle not in (0, 30, 45, 60):
        raise ValueError('Проверьте ширину пропила, толщину материала и угол реза.')
    if angle and not thickness:
        raise ValueError('Для наклонного реза укажите толщину материала.')
    # Preserve the existing long-side / alternating-cut convention.
    inset = {0: 0, 30: math.ceil(math.sqrt(3) * thickness / 3),
             45: thickness, 60: math.ceil(math.sqrt(3) * thickness)}[angle]
    effective = [Decimal(str(x)) - 2 * Decimal(str(inset)) + Decimal(str(blade)) for x in lengths]
    if any(x <= 0 for x in effective):
        raise ValueError('Длина детали слишком мала для выбранного угла и толщины.')
    scale = 10 ** max([0] + [-x.as_tuple().exponent for x in effective])
    sizes = [int(x * scale) for x in effective]
    stock_units = sorted(set(int(Decimal(str(x)) * scale) for x in stocks))
    if any(q and size > max(stock_units) for size, q in zip(sizes, counts)):
        raise ValueError('Деталь с учётом пропила не помещается ни в одну исходную заготовку.')
    patterns = []
    deadline = time.monotonic() + 5
    visits = 0

    def enumerate_patterns(index, remaining, row, stock):
        nonlocal visits
        visits += 1
        if visits > 500000 or len(patterns) >= 50000 or time.monotonic() > deadline:
            raise ValueError('Слишком много вариантов раскроя. Разделите заказ на несколько расчётов.')
        if index == len(sizes):
            if any(row):
                patterns.append((stock, tuple(row), remaining))
            return
        for quantity in range(min(counts[index], remaining // sizes[index]) + 1):
            enumerate_patterns(index + 1, remaining - quantity * sizes[index], row + [quantity], stock)

    for stock in stock_units:
        enumerate_patterns(0, stock, [], stock)
    problem = pulp.LpProblem('cutting_stock', pulp.LpMinimize)
    variables = [pulp.LpVariable(f'pattern_{i}', 0, sum(counts), cat='Integer') for i in range(len(patterns))]
    # Consumed stock minimizes total remainder for a fixed, exact order.
    # The secondary objective prefers fewer bars on equal material consumption.
    weight = sum(counts) + 1
    problem += pulp.lpSum((stock * weight + 1) * var for (stock, _, _), var in zip(patterns, variables))
    for index, quantity in enumerate(counts):
        problem += pulp.lpSum(row[index] * var for (_, row, _), var in zip(patterns, variables)) == quantity
    problem.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=20))
    if problem.sol_status != pulp.LpSolutionOptimal:
        raise ValueError('Не удалось подтвердить оптимальный раскрой за отведённое время. Разделите заказ.')
    maps, result_maps, stock_lengths = [], [], []
    totals = [0] * len(counts)
    for (stock, row, remaining), var in zip(patterns, variables):
        value = var.value()
        if value is None or abs(value - round(value)) > 1e-5:
            raise ValueError('Решатель не вернул целочисленный раскрой.')
        for _ in range(round(value)):
            remainder = remaining / scale
            maps.append([*row, remainder])
            result_maps.append([length for length, quantity in zip(lengths, row) for _ in range(quantity)] + [remainder])
            stock_lengths.append(stock / scale)
            totals = [a + b for a, b in zip(totals, row)]
    if totals != counts:
        raise ValueError('Результат не соответствует количеству деталей в заказе.')
    total_stock = sum(stock_lengths)
    total_remain = sum(row[-1] for row in maps)
    return {'maps': maps, 'result_maps': result_maps, 'stock_lengths': stock_lengths,
            'summary': {'stock_count': len(maps), 'part_count': sum(counts),
                        'total_stock': total_stock, 'total_remainder': total_remain,
                        'kerf_loss': blade * sum(counts), 'optimal': True}}
