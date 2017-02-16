import os
import random
import string


def get_path(relative_path=None):
    """ Return an absolute path to a project relative path. """

    path_components = [os.path.dirname(__file__), "..", ".."]
    root_path = os.path.abspath(os.path.join(*path_components))

    if relative_path is None:
        return root_path
    else:
        return os.path.abspath(os.path.join(root_path, relative_path))


def random_string(n):
    ''' Generate a cryptographically secure random string of length `n`. '''
    rand = random.SystemRandom()
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return ''.join(rand.choice(chars) for _ in range(n))


def random_password():
    """
    Generate 12 character password with at least:

     * 1 uppercase character
     * 1 lower case character
     * 3 digits
    """
    rand = random.SystemRandom()
    chars = string.ascii_letters + string.digits

    while True:
        password = ''.join(rand.choice(chars) for i in range(12))

        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= 3):
            break

    return password
