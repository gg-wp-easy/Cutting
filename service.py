import json

import pulp
from pulp import PULP_CBC_CMD
import math

""" здесь начинается описание сервисных функций"""
""" %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% """


# функция состаления опций резки для бд
def create_cutting_options(original_length, cuts_length, cuts_count, blade, thickness, angle):
    dict_option = {}
    dict_option['original_length'] = original_length
    dict_option['cuts_length'] = cuts_length
    dict_option['cuts_count'] = cuts_count
    dict_option['blade'] = blade
    dict_option['thickness'] = thickness
    dict_option['angle'] = angle

    return dict_option


# функция записи в json файл
def write_in_json(data, file_name):
    try:
        with open(file_name, 'r') as file:
            data_json = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data_json = []

    data_json.append(data)
    with open(file_name, 'w') as file:
        json.dump(data_json, file, indent=4)


# функция для восстановления исходных данных с учетом угла реза и толщины лезвия
# ----------------------------------------------------------------------------------------------------------------------
def restore_cuts(maps, linear_cutting, blade_thickness):
    for i in range(len(maps)):
        for j in range(len(maps[i])):
            # if j == 0:
            # maps[i][j] = maps[i][j] + 2 * linear_cutting - blade_thickness
            if j != len(maps[i]) - 1:
                maps[i][j] = maps[i][j] + 2 * linear_cutting - blade_thickness


# ----------------------------------------------------------------------------------------------------------------------

# функция для подготовки исходных заготовок с учетом угла реза
# ----------------------------------------------------------------------------------------------------------------------
def prepare_cuts(original_length, cuts_length, blade_thickness, cutting_angle, original_thickness):
    length_cutting = 0
    if cutting_angle == 0:
        length_cutting = 0
    elif cutting_angle == 30:
        length_cutting = math.ceil((math.sqrt(3) * original_thickness) / 3)
    elif cutting_angle == 60:
        length_cutting = math.ceil(math.sqrt(3) * original_thickness)
    elif cutting_angle == 45:
        length_cutting = original_thickness

    for i in range(len(cuts_length)):
        cuts_length[i] = math.ceil(cuts_length[i] - 2 * length_cutting)
        cuts_length[i] += blade_thickness
        # Preserve fractional kerf; the optimizer uses exact decimal units.

    original_length += blade_thickness
    return length_cutting


# ----------------------------------------------------------------------------------------------------------------------

# функция приведения результатов раскроя к нужному виду (добавление остатков)
# ----------------------------------------------------------------------------------------------------------------------
def recycle_maps_remains(original_length, cuts_length, maps):
    result_maps = []
    for i in range(len(maps)):
        summ = 0
        map = []
        for j in range(len(maps[i])):
            map.append(maps[i][j])
            if maps[i][j] != 0:
                for k in range(maps[i][j]):
                    summ += cuts_length[j]
        map.append(original_length - summ)
        result_maps.append(map)
    return result_maps


# функция приведения результатов раскроя к нужному виду
# ----------------------------------------------------------------------------------------------------------------------
def reсycle_maps(original_length, cuts_length, maps):
    result_maps = []
    if not maps:
        return result_maps
    if len(cuts_length) != len(maps[0]):
        for i in range(len(maps)):
            map = []
            for j in range(len(maps[i]) - 1):
                if maps[i][j] != 0:
                    for k in range(maps[i][j]):
                        map.append(cuts_length[j])
            map.append(maps[i][-1])
            result_maps.append(map)
    else:
        for i in range(len(maps)):
            map = []
            summ = 0
            for j in range(len(maps[i])):
                if maps[i][j] != 0:
                    for k in range(maps[i][j]):
                        summ += cuts_length[j]
                        map.append(cuts_length[j])
            map.append(original_length - summ)
            result_maps.append(map)

    return result_maps


# ----------------------------------------------------------------------------------------------------------------------

# функция поэлементного сравнения двух массивов
# ----------------------------------------------------------------------------------------------------------------------
def compare_equal(arr1, arr2):
    for el1, el2 in zip(arr1, arr2):
        if el1 != el2:
            return True
        else:
            return False


# ----------------------------------------------------------------------------------------------------------------------

# функция печати массива
# ----------------------------------------------------------------------------------------------------------------------
def print_arr(A):
    for i in range(len(A)):
        print(A[i])


# ----------------------------------------------------------------------------------------------------------------------

# поэлементное суммирование массива
# ----------------------------------------------------------------------------------------------------------------------
def sum_array(arr1, arr2):
    result = []
    for i in range(len(arr1)):
        # Суммируем элементы поэлементно первых двух массивов
        sum_elements = arr1[i] + arr2[i]
        result.append(sum_elements)
    return result


# поэлементное сравнение элементов на превышение
# ----------------------------------------------------------------------------------------------------------------------
def sum_and_compare(arr1, arr2, arr3):
    result = sum_array(arr1, arr2)
    for i in range(len(result)):
        if result[i] > arr3[i]:
            return False
    return True


# ----------------------------------------------------------------------------------------------------------------------

# транспонирование матрицы
# ----------------------------------------------------------------------------------------------------------------------
def transpose_matrix(matrix):
    rows, cols = len(matrix), len(matrix[0])
    transposed = [[0 for _ in range(rows)] for _ in range(cols)]

    for i in range(rows):
        for j in range(cols):
            transposed[j][i] = matrix[i][j]

    return transposed


# ----------------------------------------------------------------------------------------------------------------------

# составление всех возможных карт раскроя, а также остатков, получаемых из каждой карты
# ----------------------------------------------------------------------------------------------------------------------
def linear_cutting(length, cut_lengths, cut_counts):
    def generate_cuts(length, cut_lengths, cut_counts, current_cut, result, remainders):
        if not cut_lengths:
            result.append(current_cut.copy() + cut_counts)
            remainders.append(length)
            return

        for i in range(min(length // cut_lengths[0], cut_counts[0]) + 1):
            generate_cuts(length - i * cut_lengths[0], cut_lengths[1:], cut_counts[1:], current_cut + [i], result,
                          remainders)

    result = []
    remainders = []
    generate_cuts(length, cut_lengths, cut_counts, [], result, remainders)
    return result, remainders
# ----------------------------------------------------------------------------------------------------------------------

# составление всех возможных карт раскроя, с несколькими заготовками
# ----------------------------------------------------------------------------------------------------------------------
def linear_cutting_multi(original_lengths, cut_lengths, cut_counts):
    results = []
    remainders_list = []

    for length in original_lengths:
        result, remainders = linear_cutting(length, cut_lengths, cut_counts)
        results.append(result)
        remainders_list.append(remainders)

    return results, remainders_list
# ----------------------------------------------------------------------------------------------------------------------

# преобразование трехмерного массива в двумерный при мульти линейном раскрое
# ----------------------------------------------------------------------------------------------------------------------
def merge_3d_array_to_2d(arr):
    merged_array = []
    for i in range(len(arr)):
        for j in range(len(arr[i])):
            merged_array.append(arr[i][j])
    return merged_array
# ----------------------------------------------------------------------------------------------------------------------

# размещение заготовок в определенной площади
# ----------------------------------------------------------------------------------------------------------------------
def place_rectangles(total_area, smaller_rectangles, smaller_rect_count):
    remaining_area = total_area
    result = []

    for i in range(len(smaller_rectangles)):
        for j in range(smaller_rect_count[i]):
            if smaller_rectangles[i] <= remaining_area:
                result.append(smaller_rectangles[i])
                remaining_area -= smaller_rectangles[i]

    if remaining_area == 0:
        return result
    else:
        return []
# ----------------------------------------------------------------------------------------------------------------------

""" %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% """
""" здесь заканчивается описание сервисных функци"""

""" здесь начинается описание методов решения задач раскроя"""
""" %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% """
def linear_cut_method_multi(original_length, cuts_length, cuts_count):
    from optimizer import optimize
    return optimize(original_length, cuts_length, cuts_count)['maps']


def linear_cut_method(original_length, cuts_length, cuts_count):
    from optimizer import optimize
    return [row[:-1] for row in optimize([original_length], cuts_length, cuts_count)['maps']]


def find_optimal_maps(original_length, cuts_length, counts):
    from optimizer import optimize
    return optimize([original_length], cuts_length, counts)['maps']


# размещение двумерных заготовок на площади
# ----------------------------------------------------------------------------------------------------------------------
def greedy_cutting_stock(pieces, material_width, material_height):
    pieces = sorted(pieces, key=lambda x: x[0] * x[1], reverse=True)  # Сортируем заготовки по убыванию площади
    remaining_material = material_width * material_height
    used_pieces = []

    while remaining_material > 0:
        best_piece_index = -1
        best_fit = 0

        for i, piece in enumerate(pieces):
            if piece[0] <= material_width and piece[1] <= material_height:
                fit = min(material_width // piece[0], material_height // piece[1])
                if fit > best_fit:
                    best_fit = fit
                    best_piece_index = i

        if best_piece_index == -1:  # Не нашли подходящей заготовки
            break

        used_pieces.append(pieces[best_piece_index])
        piece_width, piece_height = pieces[best_piece_index][0], pieces[best_piece_index][1]
        area = piece_width * piece_height
        remaining_material -= area
        material_width -= piece_width
        material_height -= piece_height
        pieces.pop(best_piece_index)

    return used_pieces
# ----------------------------------------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------------------------------------
""" здесь заканчивается описание методов раскроя"""
