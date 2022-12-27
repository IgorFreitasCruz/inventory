import re
from datetime import datetime, timedelta

import jwt
from django.conf import settings
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from user_control.models import CustomUser


def get_access_token(payload, days):
    token = jwt.encode(
        {"exp": datetime.now() + timedelta(days=days), **payload},
        settings.SECRET_KEY,
        algorithm="HS256",
    )

    return token


def decodeJWT(bearer):
    if not bearer:
        return None

    token = bearer[7:]

    try:
        decode = jwt.decode(token, key=settings.SECRET_KEY, algorithms="HS256")
    except Exception:
        return None

    if decode:
        try:
            return CustomUser.objects.get(id=decode["user_id"])
        except Exception:
            return None


class CustomPagination(PageNumberPagination):
    page_size = 20


def normalize_query(
    query_string,
    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
    normspace=re.compile(r"\s{2,}").sub,
):
    """Splits the query string in invidual keywords, getting rid of unecessary spaces
    and grouping quoted words together.
    Example:

    >>> normalize_query('  some random  words "with   quotes  " and   spaces')
    ['some', 'random', 'words', 'with quotes', 'and', 'spaces']

    """
    return [normspace(" ", (t[0] or t[1]).strip()) for t in findterms(query_string)]


def get_query(query_string, search_fields):
    """Returns a query, that is a combination of Q objects. That combination
    aims to search keywords within a model by testing the given search fields.

    """
    query = None  # Query to search for every search term
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None  # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query & or_query
    return query
