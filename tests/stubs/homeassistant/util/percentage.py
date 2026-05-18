def ordered_list_item_to_percentage(ordered_list, item):
    index = ordered_list.index(item) + 1
    return int(index / len(ordered_list) * 100)

def percentage_to_ordered_list_item(ordered_list, percentage):
    index = max(0, min(len(ordered_list) - 1, round(percentage / 100 * len(ordered_list)) - 1))
    return ordered_list[index]
