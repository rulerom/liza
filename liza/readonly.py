"""Call-scoped readonly capabilities; separate from non-consuming adapters."""

def projection_root(node):
    while node.kind == 'field':
        node = node.args[0]
    return node.token.text if node.kind == 'name' else None


def readonly_root(node, names):
    root = projection_root(node)
    return root if root in names else None


def parameter_modes(signature, arguments, readonly_names):
    return ['readonly' if i in signature.readonly_params or
            (i in signature.readonly_borrowed_params and readonly_root(arg, readonly_names))
            else 'borrow' if i in signature.borrowed_params else 'value'
            for i,arg in enumerate(arguments)]
