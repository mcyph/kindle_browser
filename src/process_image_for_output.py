import numpy
import array
from PIL import Image
from numba import jit, uint, uint32
from numba.typed import List


@jit(nopython=True,
     signature_or_function=uint[:](uint[:], uint[:]),
     locals={'current_item': uint,
             'current_count': uint,
             'DIVISOR': uint,
             'SINGLE_VALUES_FROM': uint,
             'y': uint32})
def run_length_encode(out_array, in_array):
    DIVISOR = 64  # = 4 individual shades
    # May as well reserve values from a certain number for single items
    SINGLE_VALUES_FROM = (255 // DIVISOR) + 1

    current_item = 255
    current_count = 0
    y = 0

    for x in range(in_array.shape[0]):
        item = in_array[x] // DIVISOR  # Note double-division here!

        if item == current_item and current_count < 255:
            # Same item
            current_count += 1
        elif current_item == 255:
            # First item
            current_item = item
            current_count = 1
        else:
            if current_count == 1:
                out_array[y] = SINGLE_VALUES_FROM + current_item
                y += 1
            else:
                out_array[y] = current_item
                y += 1
                out_array[y] = current_count
                y += 1

            current_item = item
            current_count = 1

    if current_item != 255:
        if current_count == 1:
            out_array[y] = SINGLE_VALUES_FROM + current_item
            y += 1
        else:
            out_array[y] = current_item
            y += 1
            out_array[y] = current_count
            y += 1

    return out_array[:y-1]


def process_image_for_output(image: Image):
    print("Processing image for output...", end='')
    print("IMAGE SIZE:", image.size)
    data = numpy.asarray(image.convert('L', dither=Image.NONE)).flatten()
    out_array = numpy.ndarray(shape=(data[0]*4), dtype=numpy.uint8)
    out_array = run_length_encode(out_array, data)
    data = out_array.asbytes()
    print(' [Done]')
    return data


if __name__ == '__main__':
    TEST_DATA = [22, 22, 22, 22, 55, 55, 55, 100, 0, 200, 0, 0]
    TEST_DATA_NP = numpy.array(TEST_DATA, dtype=numpy.uint8)
    TEST_DATA_NP_EXTENDED = numpy.array(TEST_DATA*100, dtype=numpy.uint8)

    out_array = numpy.ndarray(shape=(len(TEST_DATA) * 2,), dtype=numpy.uint8)
    print(run_length_encode(out_array, TEST_DATA_NP))

    for x in range(10000):
        out_array = numpy.ndarray(shape=(len(TEST_DATA_NP_EXTENDED) * 2,), dtype=numpy.uint8)
        run_length_encode(out_array, TEST_DATA_NP_EXTENDED)
    print("DONE!")
