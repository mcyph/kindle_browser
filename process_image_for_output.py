import io
import base64
from collections import deque
from itertools import groupby, chain, repeat, count

from PIL import Image, ImageEnhance, ImageOps


def process_image_for_output(image: Image) -> str:
    print("Processing image for output...", end='')
    image = image.convert('L', dither=Image.NONE)
    #image = image.resize((image.width, image.height), resample=Image.Resampling.BILINEAR)

    #enhancer = ImageEnhance.Contrast(image)
    #image = enhancer.enhance(4.0)
    #enhancer = ImageEnhance.Sharpness(image)
    #image = enhancer.enhance(4.0)
    #image = ImageOps.grayscale(image)
    
    #image = image.convert('L')

    def process(x):
        if x < 64:
            return 0
        elif x < 128:
            return 1
        elif x < 192:
            return 2
        elif x < 220:
            return 3
        else:
            return 4

    image = image.point(process, 'L')
    #image = image.convert('1')
    #image = image.convert('L')

    pixels = list(image.getdata())
    width, height = image.size
    pixels = [pixels[i * width:(i + 1) * width] for i in range(height)]
    rle_encoded = [list(run_length.encode(i)) for i in pixels]
    # .replace('(255, 1), (0, 1)', '(1, 2)') \
    #                                    .replace('(0, 1), (255, 1)', '(1, 2)') \
    #
    rle_encoded = repr(rle_encoded).replace('), (', ',') \
                                   .replace(', ', ',') \
                                   .replace('[(', '[') \
                                   .replace(')]', ']')
    rle_encoded = eval(rle_encoded)

    #print(rle_encoded)
    
    #buf = io.BytesIO()
    #image.save(buf, format='PNG')
    #r = base64.b64encode(buf.getvalue()).decode('ascii')
    print(' [Done]')
    return rle_encoded


def ilen(iterable):
    """Return the number of items in *iterable*.
        >>> ilen(x for x in range(1000000) if x % 3 == 0)
        333334
    This consumes the iterable, so handle with care.
    """
    # This approach was selected because benchmarks showed it's likely the
    # fastest of the known implementations at the time of writing.
    # See GitHub tracker: #236, #230.
    counter = count()
    deque(zip(iterable, counter), maxlen=0)
    return next(counter)


class run_length:
    """
    :func:`run_length.encode` compresses an iterable with run-length encoding.
    It yields groups of repeated items with the count of how many times they
    were repeated:
        >>> uncompressed = 'abbcccdddd'
        >>> list(run_length.encode(uncompressed))
        [('a', 1), ('b', 2), ('c', 3), ('d', 4)]
    :func:`run_length.decode` decompresses an iterable that was previously
    compressed with run-length encoding. It yields the items of the
    decompressed iterable:
        >>> compressed = [('a', 1), ('b', 2), ('c', 3), ('d', 4)]
        >>> list(run_length.decode(compressed))
        ['a', 'b', 'b', 'c', 'c', 'c', 'd', 'd', 'd', 'd']
    """

    @staticmethod
    def encode(iterable):
        return ((k, ilen(g)) for k, g in groupby(iterable))

    @staticmethod
    def decode(iterable):
        return chain.from_iterable(repeat(k, n) for k, n in iterable)
