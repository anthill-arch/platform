class GraphQLMiddleware:
    def resolve(self, next, root, info, **args):
        raise NotImplementedError
