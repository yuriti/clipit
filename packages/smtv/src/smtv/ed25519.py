"""Ed25519 signatures (stage 27, the update channel): SMTV checks that `latest.json` was signed by the maintainers' key.

Python's standard library has no Ed25519, and none of SMTV's dependencies brings it on every system (`cryptography`
comes only with keyring on Linux), so this is the reference code of RFC 8032, unchanged in its arithmetic.
# Ported from RFC 8032, section 6 (https://www.rfc-editor.org/rfc/rfc8032#section-6), Simplified BSD License (code
# components of IETF documents, https://trustee.ietf.org/license-info): Copyright (c) 2017 IETF Trust and the persons
# identified as authors of the code (S. Josefsson, I. Liusvaara). All rights reserved. Redistribution and use in source
# and binary forms, with or without modification, are permitted provided that the conditions of the Simplified BSD
# License are met: source code keeps this notice, binary forms reproduce it in their documentation.

It is slow (milliseconds per signature) and not constant-time: fine for checking a public signature once a day, and for
signing one manifest per release on a build machine; never for anything secret on a shared computer.
"""
from __future__ import annotations

import hashlib

_P = 2 ** 255 - 19
_Q = 2 ** 252 + 27742317777372353535851937790883648493


def _inv(x: int) -> int:
    return pow(x, _P - 2, _P)


_D = -121665 * _inv(121666) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _sha512_modq(data: bytes) -> int:
    return int.from_bytes(hashlib.sha512(data).digest(), "little") % _Q


def _add(a: tuple, b: tuple) -> tuple:
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    pa, pb = (y1 - x1) * (y2 - x2) % _P, (y1 + x1) * (y2 + x2) % _P
    pc, pd = 2 * t1 * t2 * _D % _P, 2 * z1 * z2 % _P
    e, f, g, h = pb - pa, pd - pc, pd + pc, pb + pa
    return (e * f, g * h, f * g, e * h)


def _mul(s: int, point: tuple) -> tuple:
    out = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            out = _add(out, point)
        point = _add(point, point)
        s >>= 1
    return out


def _equal(a: tuple, b: tuple) -> bool:
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _recover_x(y: int, sign: int) -> int | None:
    if y >= _P:
        return None
    x2 = (y * y - 1) * _inv(_D * y * y + 1)
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x


_GY = 4 * _inv(5) % _P
_GX = _recover_x(_GY, 0) or 0
_G = (_GX, _GY, 1, _GX * _GY % _P)


def _compress(point: tuple) -> bytes:
    zinv = _inv(point[2])
    x, y = point[0] * zinv % _P, point[1] * zinv % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(data: bytes) -> tuple | None:
    if len(data) != 32:
        return None
    y = int.from_bytes(data, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def _expand(secret: bytes) -> tuple[int, bytes]:
    if len(secret) != 32:
        raise ValueError("an Ed25519 private key is 32 bytes")
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(secret: bytes) -> bytes:
    """The 32-byte public key of a 32-byte private key (seed)."""
    a, _ = _expand(secret)
    return _compress(_mul(a, _G))


def sign(secret: bytes, message: bytes) -> bytes:
    """A 64-byte signature of `message`."""
    a, prefix = _expand(secret)
    public = _compress(_mul(a, _G))
    r = _sha512_modq(prefix + message)
    rs = _compress(_mul(r, _G))
    s = (r + _sha512_modq(rs + public + message) * a) % _Q
    return rs + int.to_bytes(s, 32, "little")


def verify(public: bytes, message: bytes, signature: bytes) -> bool:
    """True only when `signature` is a valid signature of `message` by the key `public`; anything malformed is False."""
    if len(public) != 32 or len(signature) != 64:
        return False
    a = _decompress(public)
    if a is None:
        return False
    rs = signature[:32]
    r = _decompress(rs)
    if r is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _Q:
        return False
    h = _sha512_modq(rs + public + message)
    return _equal(_mul(s, _G), _add(r, _mul(h, a)))
