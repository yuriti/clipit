"""A QR code for the phone's address (stage 9), drawn as SVG. Standard library only.

Only what SMTV needs: byte mode, error correction level M, versions 1–10 (up to 213 bytes; the address is about 60).
The algorithm follows the QR standard (ISO/IEC 18004) the way Project Nayuki's reference encoder lays it out. A whole
package for this would be one more dependency in every install for a few dozen lines of arithmetic.
"""
from __future__ import annotations

# error correction level M, by version (index 0 unused)
ECC_PER_BLOCK = (-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26)
BLOCKS = (-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5)
FORMAT_M = 0          # the two format bits of level M
MAX_VERSION = 10


def _raw_modules(ver: int) -> int:
    result = (16 * ver + 128) * ver + 64
    if ver >= 2:
        n = ver // 7 + 2
        result -= (25 * n - 10) * n - 55
        if ver >= 7:
            result -= 36
    return result


def _data_codewords(ver: int) -> int:
    return _raw_modules(ver) // 8 - ECC_PER_BLOCK[ver] * BLOCKS[ver]


def _gf_mul(x: int, y: int) -> int:
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _rs_divisor(degree: int) -> list[int]:
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            result[j] = _gf_mul(result[j], root)
            if j + 1 < degree:
                result[j] ^= result[j + 1]
        root = _gf_mul(root, 0x02)
    return result


def _rs_remainder(data: bytes | list[int], divisor: list[int]) -> list[int]:
    result = [0] * len(divisor)
    for b in data:
        factor = b ^ result.pop(0)
        result.append(0)
        for i, coef in enumerate(divisor):
            result[i] ^= _gf_mul(coef, factor)
    return result


def _alignment(ver: int, size: int) -> list[int]:
    if ver == 1:
        return []
    n = ver // 7 + 2
    step = (ver * 8 + n * 3 + 5) // (n * 4 - 4) * 2
    return list(reversed([size - 7 - i * step for i in range(n - 1)] + [6]))


class QR:
    def __init__(self, text: str):
        data = text.encode("utf-8")
        for ver in range(1, MAX_VERSION + 1):
            count_bits = 8 if ver <= 9 else 16
            if 4 + count_bits + 8 * len(data) <= _data_codewords(ver) * 8:
                break
        else:
            raise ValueError(f"too long for a QR code here: {len(data)} bytes")
        self.version, self.size = ver, ver * 4 + 17
        bits = [0, 1, 0, 0] + [(len(data) >> i) & 1 for i in reversed(range(count_bits))]
        for b in data:
            bits += [(b >> i) & 1 for i in reversed(range(8))]
        cap = _data_codewords(ver) * 8
        bits += [0] * min(4, cap - len(bits))
        bits += [0] * (-len(bits) % 8)
        pad = 0xEC
        while len(bits) < cap:
            bits += [(pad >> i) & 1 for i in reversed(range(8))]
            pad ^= 0xEC ^ 0x11
        codewords = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
        self.modules = [[False] * self.size for _ in range(self.size)]
        self.function = [[False] * self.size for _ in range(self.size)]
        self._function_patterns()
        self._draw_codewords(self._interleave(codewords))
        best, best_penalty = 0, None
        for mask in range(8):
            self._apply_mask(mask)
            self._format_bits(mask)
            p = self._penalty()
            if best_penalty is None or p < best_penalty:
                best, best_penalty = mask, p
            self._apply_mask(mask)   # undo (xor)
        self._apply_mask(best)
        self._format_bits(best)

    # --- layout ---------------------------------------------------------------------------------------------

    def _set(self, x: int, y: int, dark: bool) -> None:
        self.modules[y][x] = dark
        self.function[y][x] = True

    def _function_patterns(self) -> None:
        size = self.size
        for i in range(size):
            self._set(6, i, i % 2 == 0)
            self._set(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < size and 0 <= y < size:
                        d = max(abs(dx), abs(dy))
                        self._set(x, y, d not in (2, 4))
        pos = _alignment(self.version, size)
        n = len(pos)
        for i in range(n):
            for j in range(n):
                if (i == 0 and j == 0) or (i == 0 and j == n - 1) or (i == n - 1 and j == 0):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self._set(pos[i] + dx, pos[j] + dy, max(abs(dx), abs(dy)) != 1)
        self._format_bits(0)   # reserve the format area; drawn for real after the mask is chosen
        if self.version >= 7:
            rem = self.version
            for _ in range(12):
                rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
            bits = self.version << 12 | rem
            for i in range(18):
                bit = (bits >> i) & 1 == 1
                a, b = size - 11 + i % 3, i // 3
                self._set(a, b, bit)
                self._set(b, a, bit)

    def _format_bits(self, mask: int) -> None:
        data = FORMAT_M << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412
        get = lambda i: (bits >> i) & 1 == 1  # noqa: E731
        for i in range(6):
            self._set(8, i, get(i))
        self._set(8, 7, get(6))
        self._set(8, 8, get(7))
        self._set(7, 8, get(8))
        for i in range(9, 15):
            self._set(14 - i, 8, get(i))
        size = self.size
        for i in range(8):
            self._set(size - 1 - i, 8, get(i))
        for i in range(8, 15):
            self._set(8, size - 15 + i, get(i))
        self._set(8, size - 8, True)   # the dark module

    def _interleave(self, data: list[int]) -> list[int]:
        ver = self.version
        nblocks, ecc_len = BLOCKS[ver], ECC_PER_BLOCK[ver]
        raw = _raw_modules(ver) // 8
        short = nblocks - raw % nblocks
        short_len = raw // nblocks
        divisor = _rs_divisor(ecc_len)
        blocks, k = [], 0
        for i in range(nblocks):
            dat = data[k:k + short_len - ecc_len + (0 if i < short else 1)]
            k += len(dat)
            ecc = _rs_remainder(dat, divisor)
            if i < short:
                dat = dat + [0]
            blocks.append(dat + ecc)
        out = []
        for i in range(len(blocks[0])):
            for j, blk in enumerate(blocks):
                if i != short_len - ecc_len or j >= short:
                    out.append(blk[i])
        return out

    def _draw_codewords(self, data: list[int]) -> None:
        size, i = self.size, 0
        right = size - 1
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(size):
                for j in range(2):
                    x = right - j
                    upward = (right + 1) & 2 == 0
                    y = size - 1 - vert if upward else vert
                    if not self.function[y][x] and i < len(data) * 8:
                        self.modules[y][x] = (data[i >> 3] >> (7 - (i & 7))) & 1 == 1
                        i += 1
            right -= 2

    def _apply_mask(self, mask: int) -> None:
        f = (lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
             lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
             lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
             lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0)[mask]
        for y in range(self.size):
            for x in range(self.size):
                if not self.function[y][x] and f(x, y):
                    self.modules[y][x] = not self.modules[y][x]

    def _penalty(self) -> int:
        size, m, result = self.size, self.modules, 0
        lines = [m[y] for y in range(size)] + [[m[y][x] for y in range(size)] for x in range(size)]
        for line in lines:
            run, prev = 0, None
            for v in line:
                if v == prev:
                    run += 1
                else:
                    if run >= 5:
                        result += run - 2
                    run, prev = 1, v
            if run >= 5:
                result += run - 2
            s = "".join("1" if v else "0" for v in [False] * 4 + list(line) + [False] * 4)
            for pat in ("10111010000", "00001011101"):
                start = s.find(pat)
                while start != -1:
                    result += 40
                    start = s.find(pat, start + 1)
        for y in range(size - 1):
            for x in range(size - 1):
                if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    result += 3
        dark = sum(v for row in m for v in row)
        total = size * size
        k = (abs(dark * 20 - total * 10) + total - 1) // total - 1
        return result + k * 10

    # --- output -----------------------------------------------------------------------------------------------

    def svg(self, border: int = 4) -> str:
        """Black modules on white with a quiet zone: phone cameras read it in any theme."""
        n = self.size + border * 2
        path = "".join(f"M{x + border},{y + border}h1v1h-1z" for y in range(self.size) for x in range(self.size) if self.modules[y][x])
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
                f'<rect width="{n}" height="{n}" fill="#fff"/><path d="{path}" fill="#000"/></svg>')


def svg(text: str) -> str:
    return QR(text).svg()
