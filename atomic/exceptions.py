class TransactionError(Exception):
    pass


class TransactionTimeoutError(Exception):
    pass


class TransactionFinished(Exception):
    pass
