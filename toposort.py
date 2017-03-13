
def topological_sort(l, get_depends):

    result = []
    marked = set()
    temporary_marked = set()

    def visit(n):
        if n in marked:
            return
        if n in temporary_marked:
            raise TypeError("Not a DAG")
        temporary_marked.add(n)
        for m in get_depends(n):
            visit(m)
        marked.add(n)
        result.append(n)

    for n in l:
        visit(n)

    return result

if __name__ == '__main__':

    # --- Beispiel 1

    l = [1, 2, 3, 4, 5, 6, 7]

    # in Worten: 1 haengt von 2 ab, 2 von 3, ... 6 von 7, 7 von nichts mehr
    def get_depends(n):
        if n == 7:
            return []
        else:
            return [n + 1]

    # liefert: [7, 6, 5, 4, 3, 2, 1]
    print topological_sort(l, get_depends)

    # --- Beispiel 2

    l = {
        1 : (2 ,3),
        2 : (4,),
        3 : (2,),
        4 : ()
    }

    # liefert: [4, 2, 3, 1]
    print topological_sort(l.keys(), lambda key: l[key])
