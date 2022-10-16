import numpy
import array
from PIL import Image
from numba import jit, u8
from numba.typed import List


@jit(forceobj=True,  # WARNING!
     locals={'current_item': u8,
             'current_count': u8,
             'DIVISOR': u8,
             'SINGLE_VALUES_FROM': u8})
def run_length_encode(in_array):
    DIVISOR = 64  # = 4 individual shades
    # May as well reserve values from a certain number for single items
    SINGLE_VALUES_FROM = (255 // DIVISOR) + 1

    out_array = bytearray()
    current_item = 255
    current_count = 0

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
                out_array.append(SINGLE_VALUES_FROM + current_item)
            else:
                out_array.append(current_item)
                out_array.append(current_count)

            current_item = item
            current_count = 1

    if current_item != 255:
        if current_count == 1:
            out_array.append(SINGLE_VALUES_FROM + current_item)
        else:
            out_array.append(current_item)
            out_array.append(current_count)

    return out_array


def process_image_for_output(image: Image):
    print("Processing image for output...", end='')
    print("IMAGE SIZE:", image.size)
    data = numpy.asarray(image.convert('L', dither=Image.NONE)).flatten()
    data = run_length_encode(data)
    print(' [Done]')
    return data


if __name__ == '__main__':
    TEST_DATA = [22, 22, 22, 22, 55, 55, 55, 100, 0, 200, 0, 0]
    TEST_DATA_NP = numpy.array(TEST_DATA, dtype=numpy.uint8)
    TEST_DATA_NP_EXTENDED = numpy.array(TEST_DATA*100, dtype=numpy.uint8)
    print(run_length_encode(TEST_DATA_NP))

    for x in range(10000):
        run_length_encode(TEST_DATA_NP_EXTENDED)
    print("DONE!")
