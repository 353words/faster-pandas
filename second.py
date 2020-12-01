def second_for(values):
    first, second = -1, -1
    for val in values:
        if val > first:
            first, second = val, first
        elif val > second:
            second = val
    return second


def second_sort(values):
    values = sorted(values)
    return values[-2]
