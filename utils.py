# coding=utf-8
# Archivo: 
# Autor: Ventura Pérez García - vetu@pm.me - github.com/vetu11
# Fecha última edición: 
# Descripción:


def join_unicode_list(list, space=None):
    # Junta los str o unicodes aportados en la lista en uno solo, y pone un separador entre medias si se especifica.

    result = unicode()
    result += list[0]

    for u in list[1:]:
        result += space + u if space is not None else u
    return result


def lerp(min, max, i):
    # Interpolación lineal.

    return (max - min) * i + min
