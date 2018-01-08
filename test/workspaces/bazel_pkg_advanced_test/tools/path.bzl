def dirname(p, remove=1):
    pieces = p.split('/')
    return '/'.join(pieces[0:-remove])
